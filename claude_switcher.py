#!/usr/bin/env python3
"""Claude configuration switcher - manage multiple Claude environment configs."""

import argparse
import json
import logging
import os
import sys
import tempfile
import subprocess
from pathlib import Path

# ========== CONFIG START ==========
CONFIGS = {
    "default": {
        "env": {
            "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
            "ANTHROPIC_BASE_URL": "https://sk.xxx.com"
        },
        "permissions": {
            "allow": [],
            "deny": []
        }
    }
}
# ========== CONFIG END ==========

logger = logging.getLogger(__name__)

CLAUDE_CONFIG_PATH = Path.home() / ".claude" / "settings.json"


class ClaudeConfigManager:
    """Claude配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.configs = CONFIGS
        self.ensure_claude_dir_exists()

    def ensure_claude_dir_exists(self):
        """确保.claude目录存在"""
        claude_dir = CLAUDE_CONFIG_PATH.parent
        try:
            claude_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"无法创建目录 {claude_dir}: {e}", file=sys.stderr)
            sys.exit(1)

    def validate_json(self, data):
        """验证JSON格式的合法性"""
        try:
            json.dumps(data)
            return True
        except (TypeError, ValueError):
            return False

    def list_configs(self):
        """列出所有配置名称"""
        if not self.configs:
            print("当前没有保存的配置")
            return
        print("可用的配置:")
        for name in sorted(self.configs.keys()):
            print(f"  - {name}")

    def switch_config(self, config_name):
        """切换到指定配置"""
        if config_name not in self.configs:
            print(f"错误: 配置 '{config_name}' 不存在", file=sys.stderr)
            return

        config = self.configs[config_name]

        # 验证配置合法性
        if not self.validate_json(config):
            print(f"错误: 配置 '{config_name}' 包含无效的JSON", file=sys.stderr)
            return

        try:
            with open(CLAUDE_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"成功切换到配置: {config_name}")
        except IOError as e:
            print(f"写入配置文件失败: {e}", file=sys.stderr)

    def new_config(self, config_name):
        """创建新的配置"""
        if not config_name:
            print("错误: 配置名称不能为空", file=sys.stderr)
            return

        if config_name in self.configs:
            print(f"错误: 配置 '{config_name}' 已存在", file=sys.stderr)
            return

        template = self.configs.get("default", {})
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
            json.dump(template, tmp_file, indent=2, ensure_ascii=False)
            tmp_file_path = tmp_file.name

        try:
            editor = os.environ.get('EDITOR', 'vim')
            subprocess.run([editor, tmp_file_path], check=True)

            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                try:
                    new_config = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"错误: 无效的JSON格式 - {e}", file=sys.stderr)
                    return

            if not self.validate_json(new_config):
                print("错误: 配置格式无效", file=sys.stderr)
                return

            self.configs[config_name] = new_config
            self.save_configs_to_file()
            print(f"成功创建配置: {config_name}")

        except subprocess.CalledProcessError:
            print("用户取消了编辑", file=sys.stderr)
        except Exception as e:
            print(f"创建配置时出错: {e}", file=sys.stderr)
        finally:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass

    def delete_config(self, config_name):
        """删除指定配置"""
        if config_name not in self.configs:
            print(f"错误: 配置 '{config_name}' 不存在", file=sys.stderr)
            return
        if config_name == "default":
            print("错误: 不能删除默认配置", file=sys.stderr)
            return
        del self.configs[config_name]
        self.save_configs_to_file()
        print(f"成功删除配置: {config_name}")

    def peek_config(self, config_name):
        """查看指定配置内容（不切换）"""
        if config_name not in self.configs:
            print(f"错误: 配置 '{config_name}' 不存在", file=sys.stderr)
            return
        print(json.dumps(self.configs[config_name], indent=2, ensure_ascii=False))

    def import_config(self, config_name):
        """从 ~/.claude/settings.json 导入配置"""
        if not config_name:
            print("错误: 配置名称不能为空", file=sys.stderr)
            return

        if config_name in self.configs:
            print(f"错误: 配置 '{config_name}' 已存在", file=sys.stderr)
            return

        if not CLAUDE_CONFIG_PATH.exists():
            print(f"错误: 配置文件不存在 {CLAUDE_CONFIG_PATH}", file=sys.stderr)
            return

        try:
            with open(CLAUDE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"错误: 无效的JSON格式 - {e}", file=sys.stderr)
            return
        except IOError as e:
            print(f"错误: 无法读取配置文件 - {e}", file=sys.stderr)
            return

        if not self.validate_json(config):
            print("错误: 配置格式无效", file=sys.stderr)
            return

        self.configs[config_name] = config
        self.save_configs_to_file()
        print(f"成功导入配置: {config_name}")

    def save_configs_to_file(self):
        """将配置保存到当前Python文件"""
        try:
            current_file = Path(__file__).resolve()
            content = current_file.read_text(encoding='utf-8')

            # 定位 CONFIG START 和 CONFIG END
            start_marker = '# ========== CONFIG START ==========\n'
            end_marker = '\n# ========== CONFIG END =========='

            start_pos = content.find(start_marker)
            end_pos = content.find(end_marker)

            if start_pos == -1 or end_pos == -1:
                print("警告: 无法找到CONFIG标记，配置可能未保存", file=sys.stderr)
                return

            # 生成新的CONFIG段
            json_str = json.dumps(self.configs, ensure_ascii=False, indent=4)
            new_config = f'CONFIGS = {json_str}'

            # 替换CONFIG块内容（保持标记）
            new_content = (
                content[:start_pos + len(start_marker)] +
                new_config +
                content[end_pos:]
            )

            current_file.write_text(new_content, encoding='utf-8')
        except Exception as e:
            print(f"保存配置到文件时出错: {e}", file=sys.stderr)


HELP_TEXT = """命令:
  list                   列出所有可用的配置
  switch NAME            切换到指定的配置
  new NAME               创建新的配置
  import NAME            从 ~/.claude/settings.json 导入配置
  delete NAME            删除指定的配置
  peek NAME              查看指定配置内容
  help                   显示此帮助信息

示例:
  python claude_switcher.py list
  python claude_switcher.py switch work
  python claude_switcher.py new home
  python claude_switcher.py import current
  python claude_switcher.py delete temp
  python claude_switcher.py peek default

配置文件位置: ~/.claude/settings.json
"""

def print_help():
    print(HELP_TEXT)


def main():
    parser = argparse.ArgumentParser(
        description="Manage multiple Claude environment configurations",
        add_help=False,
        usage="python claude_switcher.py <command> [options]"
    )
    subparsers = parser.add_subparsers(title='commands', dest="command")

    subparsers.add_parser('list', help='列出所有配置')

    switch_p = subparsers.add_parser('switch', help='切换到指定配置')
    switch_p.add_argument('name', help='配置名称')

    new_p = subparsers.add_parser('new', help='创建新配置')
    new_p.add_argument('name', help='新配置名称')

    import_p = subparsers.add_parser('import', help='从 ~/.claude/settings.json 导入配置')
    import_p.add_argument('name', help='新配置名称')

    delete_p = subparsers.add_parser('delete', help='删除指定配置')
    delete_p.add_argument('name', help='配置名称')

    peek_p = subparsers.add_parser('peek', help='查看指定配置内容')
    peek_p.add_argument('name', help='配置名称')

    subparsers.add_parser('help', help='显示帮助信息')

    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    args = parser.parse_args()

    # 创建配置管理器
    manager = ClaudeConfigManager()

    if args.command in (None, 'help'):
        print_help()
    elif args.command == 'list':
        manager.list_configs()
    elif args.command == 'switch':
        manager.switch_config(args.name)
    elif args.command == 'new':
        manager.new_config(args.name)
    elif args.command == 'import':
        manager.import_config(args.name)
    elif args.command == 'delete':
        manager.delete_config(args.name)
    elif args.command == 'peek':
        manager.peek_config(args.name)
    else:
        print_help()


if __name__ == "__main__":
    main()
