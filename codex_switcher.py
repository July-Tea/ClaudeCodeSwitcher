#!/usr/bin/env python3
"""Manage complete Codex configurations as named profiles."""

import argparse
import ast
import copy
import json
import os
import pprint
import shlex
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and earlier
    tomllib = None


# ========== CONFIG START ==========
CONFIGS = {   'default': {   'auth': {'OPENAI_API_KEY': 'sk-xxx', 'auth_mode': 'apikey'},
                   'config_toml': 'model = "gpt-5"\n'}}
# ========== CONFIG END ==========


AUTH_PATH = Path.home() / ".codex" / "auth.json"
CONFIG_PATH = Path.home() / ".codex" / "config.toml"
START_MARKER = "# ========== CONFIG START =========="
END_MARKER = "# ========== CONFIG END =========="


class ConfigError(ValueError):
    """A user-facing configuration or filesystem error."""


@dataclass(frozen=True)
class FileSnapshot:
    exists: bool
    data: bytes = b""
    mode: int = 0o600


class CodexConfigManager:
    def __init__(
        self,
        configs=None,
        auth_path=None,
        config_path=None,
        source_path=None,
    ):
        self.configs = CONFIGS if configs is None else configs
        self.auth_path = Path(auth_path) if auth_path else AUTH_PATH
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.source_path = Path(source_path) if source_path else Path(__file__).resolve()

    def validate_profile(self, profile):
        if not isinstance(profile, dict):
            raise ConfigError("配置必须是对象")
        if "auth" not in profile or "config_toml" not in profile:
            raise ConfigError("配置必须同时包含 auth 和 config_toml")
        if not isinstance(profile["auth"], dict):
            raise ConfigError("auth 必须是 JSON 对象")
        if not isinstance(profile["config_toml"], str):
            raise ConfigError("config_toml 必须是字符串")
        try:
            json.dumps(profile["auth"], ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"auth 不是有效的 JSON 数据: {exc}") from exc
        self._validate_toml(profile["config_toml"])

    @staticmethod
    def _validate_toml(value):
        if not value.strip():
            raise ConfigError("config_toml 不能为空")
        if "\x00" in value:
            raise ConfigError("config_toml 包含无效的 NUL 字符")
        if tomllib is not None:
            try:
                return tomllib.loads(value)
            except tomllib.TOMLDecodeError as exc:
                raise ConfigError(f"config_toml 不是有效的 TOML: {exc}") from exc
        return value

    def _read_live_profile(self):
        if not self.auth_path.is_file() or not self.config_path.is_file():
            return None
        try:
            auth = json.loads(self.auth_path.read_text(encoding="utf-8"))
            config_toml = self.config_path.read_text(encoding="utf-8")
            profile = {"auth": auth, "config_toml": config_toml}
            self.validate_profile(profile)
            return profile
        except (OSError, json.JSONDecodeError, ConfigError):
            return None

    @staticmethod
    def _profiles_equal(left, right):
        try:
            if left["auth"] != right["auth"]:
                return False
            if tomllib is None:
                return left["config_toml"] == right["config_toml"]
            return tomllib.loads(left["config_toml"]) == tomllib.loads(
                right["config_toml"]
            )
        except (KeyError, TypeError, ValueError):
            return False

    def find_current_profile(self):
        live = self._read_live_profile()
        if live is None:
            return None
        for name in sorted(self.configs):
            profile = self.configs[name]
            try:
                self.validate_profile(profile)
            except ConfigError:
                continue
            if self._profiles_equal(live, profile):
                return name
        return None

    @staticmethod
    def _snapshot(path):
        if not path.exists():
            return FileSnapshot(False)
        try:
            return FileSnapshot(
                True,
                path.read_bytes(),
                stat.S_IMODE(path.stat().st_mode),
            )
        except OSError as exc:
            raise ConfigError(f"无法读取现有文件 {path}: {exc}") from exc

    def _replace_file(self, path, data, mode):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, mode)
            os.replace(temp_path, path)
            temp_path = None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def _restore_snapshot(self, path, snapshot):
        if snapshot.exists:
            self._replace_file_direct(path, snapshot.data, snapshot.mode)
        else:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _replace_file_direct(path, data, mode):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, mode)
            os.replace(temp_path, path)
            temp_path = None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def switch_config(self, name):
        if name not in self.configs:
            raise ConfigError(f"配置 '{name}' 不存在")
        profile = self.configs[name]
        self.validate_profile(profile)

        auth_snapshot = self._snapshot(self.auth_path)
        config_snapshot = self._snapshot(self.config_path)
        auth_data = json.dumps(
            profile["auth"], indent=2, ensure_ascii=False
        ).encode("utf-8") + b"\n"
        config_data = profile["config_toml"].encode("utf-8")
        config_mode = config_snapshot.mode if config_snapshot.exists else 0o600

        try:
            self._replace_file(self.auth_path, auth_data, 0o600)
            self._replace_file(self.config_path, config_data, config_mode)
        except OSError as exc:
            rollback_errors = []
            for path, snapshot in (
                (self.auth_path, auth_snapshot),
                (self.config_path, config_snapshot),
            ):
                try:
                    self._restore_snapshot(path, snapshot)
                except OSError as rollback_exc:
                    rollback_errors.append(f"{path}: {rollback_exc}")
            detail = f"切换失败，已恢复原配置: {exc}"
            if rollback_errors:
                detail = "切换和回滚均失败，当前配置可能不一致: " + "; ".join(
                    rollback_errors
                )
            raise ConfigError(detail) from exc

    def save_configs_to_file(self):
        try:
            content = self.source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"无法读取脚本 {self.source_path}: {exc}") from exc

        start = content.find(START_MARKER)
        end = content.find(END_MARKER)
        if start < 0 or end < 0 or end <= start:
            raise ConfigError("无法找到 CONFIG 标记，配置未保存")

        start_line_end = content.find("\n", start)
        if start_line_end < 0:
            raise ConfigError("CONFIG START 标记格式无效")
        rendered = pprint.pformat(
            self.configs,
            indent=4,
            sort_dicts=True,
            width=100,
        )
        new_content = (
            content[: start_line_end + 1]
            + f"CONFIGS = {rendered}\n"
            + content[end:]
        )
        try:
            ast.parse(new_content, filename=str(self.source_path))
        except SyntaxError as exc:
            raise ConfigError(f"生成的脚本语法无效，配置未保存: {exc}") from exc

        mode = stat.S_IMODE(self.source_path.stat().st_mode)
        try:
            self._replace_file(self.source_path, new_content.encode("utf-8"), mode)
        except OSError as exc:
            raise ConfigError(f"保存配置到脚本失败: {exc}") from exc

    def import_config(self, name):
        if not name:
            raise ConfigError("配置名称不能为空")
        if name in self.configs:
            raise ConfigError(f"配置 '{name}' 已存在")
        if not self.auth_path.is_file() or not self.config_path.is_file():
            raise ConfigError("导入需要 auth.json 和 config.toml 同时存在")
        try:
            profile = {
                "auth": json.loads(self.auth_path.read_text(encoding="utf-8")),
                "config_toml": self.config_path.read_text(encoding="utf-8"),
            }
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"读取当前配置失败: {exc}") from exc
        self.validate_profile(profile)
        self.configs[name] = profile
        try:
            self.save_configs_to_file()
        except ConfigError:
            del self.configs[name]
            raise

    def _edit_value(self, value, target):
        suffix = ".json" if target == "auth" else ".toml"
        if target == "auth":
            initial = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        else:
            initial = value
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, encoding="utf-8", delete=False
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(initial)
            editor = shlex.split(os.environ.get("EDITOR", "vim"))
            subprocess.run([*editor, str(temp_path)], check=True)
            edited_text = temp_path.read_text(encoding="utf-8")
            if target == "auth":
                edited = json.loads(edited_text)
                if not isinstance(edited, dict):
                    raise ConfigError("auth 必须是 JSON 对象")
                return edited
            self._validate_toml(edited_text)
            return edited_text
        except subprocess.CalledProcessError:
            return None
        except (OSError, json.JSONDecodeError, ConfigError) as exc:
            raise ConfigError(f"编辑后的 {target} 内容无效: {exc}") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def edit_config(self, name, target):
        if name not in self.configs:
            raise ConfigError(f"配置 '{name}' 不存在")
        if target not in {"auth", "config"}:
            raise ConfigError(f"未知编辑目标: {target}")
        original = self.configs[name]
        edited_profile = copy.deepcopy(original)
        changed = False
        key = "auth" if target == "auth" else "config_toml"
        edited = self._edit_value(edited_profile[key], target)
        if edited is None:
            return False
        if edited != edited_profile[key]:
            edited_profile[key] = edited
            changed = True
        if not changed:
            return False
        self.validate_profile(edited_profile)
        self.configs[name] = edited_profile
        try:
            self.save_configs_to_file()
        except ConfigError:
            self.configs[name] = original
            raise
        return True

    def new_config(self, name, target):
        if not name:
            raise ConfigError("配置名称不能为空")
        if name in self.configs:
            raise ConfigError(f"配置 '{name}' 已存在")
        if "default" not in self.configs:
            raise ConfigError("缺少 default 配置")
        if target not in {"auth", "config", "none"}:
            raise ConfigError(f"未知编辑目标: {target}")
        profile = copy.deepcopy(self.configs["default"])
        self.validate_profile(profile)
        targets = [] if target == "none" else [target]
        changed = False
        for item in targets:
            key = "auth" if item == "auth" else "config_toml"
            edited = self._edit_value(profile[key], item)
            if edited is None:
                return False
            if edited != profile[key]:
                profile[key] = edited
                changed = True
        if targets and not changed:
            return False
        self.validate_profile(profile)
        self.configs[name] = profile
        try:
            self.save_configs_to_file()
        except ConfigError:
            del self.configs[name]
            raise
        return True

    def delete_config(self, name):
        if name not in self.configs:
            raise ConfigError(f"配置 '{name}' 不存在")
        if name == "default":
            raise ConfigError("不能删除 default 配置")
        profile = self.configs.pop(name)
        try:
            self.save_configs_to_file()
        except ConfigError:
            self.configs[name] = profile
            raise
        return True

    def peek_config(self, name):
        if name not in self.configs:
            raise ConfigError(f"配置 '{name}' 不存在")
        self.validate_profile(self.configs[name])
        return (
            "===== auth.json =====\n"
            + json.dumps(self.configs[name]["auth"], indent=2, ensure_ascii=False)
            + "\n\n===== config.toml =====\n"
            + self.configs[name]["config_toml"]
        )


def _choose(prompt, choices):
    print(prompt)
    for index, (label, _) in enumerate(choices, start=1):
        print(f"  {index}. {label}")
    value = input("请选择: ").strip()
    try:
        index = int(value) - 1
        return choices[index][1]
    except (ValueError, IndexError):
        raise ConfigError("无效的选择")


def build_parser():
    parser = argparse.ArgumentParser(
        description="管理完整的 Codex 配置",
        usage="python3 codex_switcher.py <command> [options]",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="列出所有配置")

    switch_parser = subparsers.add_parser("switch", help="切换配置")
    switch_parser.add_argument("name")

    new_parser = subparsers.add_parser("new", help="创建配置")
    new_parser.add_argument("name")

    edit_parser = subparsers.add_parser("edit", help="编辑配置")
    edit_parser.add_argument("name")
    edit_parser.add_argument("target", nargs="?", choices=("auth", "config"))

    import_parser = subparsers.add_parser("import", help="导入当前配置")
    import_parser.add_argument("name")

    delete_parser = subparsers.add_parser("delete", help="删除配置")
    delete_parser.add_argument("name")

    peek_parser = subparsers.add_parser("peek", help="查看完整配置")
    peek_parser.add_argument("name")
    subparsers.add_parser("help", help="显示帮助")
    return parser


def _print_profiles(manager):
    current = manager.find_current_profile()
    print(f"当前配置: {current or 'unmanaged'}")
    print("可用配置:")
    for name in sorted(manager.configs):
        marker = "*" if name == current else " "
        print(f"{marker} {name}")


def main(argv=None, manager=None):
    args_list = sys.argv[1:] if argv is None else list(argv)
    parser = build_parser()
    manager = manager or CodexConfigManager()
    if not args_list:
        _print_profiles(manager)
        print()
        parser.print_help()
        return 0
    args = parser.parse_args(args_list)
    try:
        if args.command == "help":
            parser.print_help()
        elif args.command == "list":
            _print_profiles(manager)
        elif args.command == "switch":
            manager.switch_config(args.name)
            print(f"成功切换到配置: {args.name}")
            print(f"  {manager.auth_path}")
            print(f"  {manager.config_path}")
        elif args.command == "new":
            if not args.name:
                raise ConfigError("配置名称不能为空")
            if args.name in manager.configs:
                raise ConfigError(f"配置 '{args.name}' 已存在")
            target = _choose(
                "新配置编辑方式:",
                [
                    ("编辑 auth.json", "auth"),
                    ("编辑 config.toml", "config"),
                    ("暂不编辑", "none"),
                ],
            )
            if manager.new_config(args.name, target):
                print(f"成功创建配置: {args.name}")
            else:
                print("已取消创建")
        elif args.command == "edit":
            target = args.target or _choose(
                "编辑内容:",
                [
                    ("auth.json", "auth"),
                    ("config.toml", "config"),
                ],
            )
            if manager.edit_config(args.name, target):
                print(f"成功修改配置: {args.name}")
            else:
                print("配置未修改")
        elif args.command == "import":
            manager.import_config(args.name)
            print(f"成功导入配置: {args.name}")
        elif args.command == "delete":
            manager.delete_config(args.name)
            print(f"成功删除配置: {args.name}")
        elif args.command == "peek":
            print(manager.peek_config(args.name), end="")
            if not manager.configs[args.name]["config_toml"].endswith("\n"):
                print()
        else:
            parser.print_help()
        return 0
    except ConfigError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
