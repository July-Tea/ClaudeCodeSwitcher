import argparse
import json
import os
import sys
import tempfile
import subprocess
from pathlib import Path

# 配置文件存储在Python文件中的变量
CONFIGS = {
    "default": {
        "env": {
            "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
            "ANTHROPIC_BASE_URL": "https://sk.xxx.com "
        },
        "permissions": {
            "allow": [],
            "deny": []
        }
    },
}

DEFAULT_CONFIG = {
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
        "ANTHROPIC_BASE_URL": "https://sk.xxx.com "
    },
    "permissions": {
        "allow": [],
        "deny": []
    }
}

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

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
            json.dump(DEFAULT_CONFIG, tmp_file, indent=2, ensure_ascii=False)
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

    def save_configs_to_file(self):
        """将配置保存到当前Python文件"""
        try:
            current_file = Path(__file__).resolve()
            with open(current_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            start_line = None
            end_line = None

            # 定位 CONFIGS 开始结束行（支持多行注释后习惯）
            for i, line in enumerate(lines):
                if line.strip().startswith('CONFIGS = {'):
                    start_line = i
                    continue
                if start_line is not None and line.strip() == "}":
                    # 检查大括号匹配（防止嵌套大括号误判）
                    bracket_count = 0
                    for j in range(start_line, i + 1):
                        if '{' in lines[j]:
                            bracket_count += lines[j].count('{')
                        if '}' in lines[j]:
                            bracket_count -= lines[j].count('}')
                    if bracket_count == 0:
                        end_line = i
                        break

            if start_line is None or end_line is None:
                print("警告: 无法找到CONFIGS变量，配置可能未保存", file=sys.stderr)
                return

            # 重新生成变量内容
            new_config_lines = [
                'CONFIGS = {\n'
            ]
            for name, config in self.configs.items():
                config_json = json.dumps(config, indent=4, ensure_ascii=False)
                config_lines = config_json.split('\n')
                config_str = '\n'.join(f'    {line}' if i > 0 else line for i, line in enumerate(config_lines))
                new_config_lines.append(f'    "{name}": {config_str},\n')
            new_config_lines.append('}\n')

            new_lines = lines[:start_line] + new_config_lines + lines[end_line + 1:]

            with open(current_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

        except Exception as e:
            print(f"保存配置到文件时出错: {e}", file=sys.stderr)


HELP_TEXT = """
Claude配置管理工具使用说明

命令:
  list                   列出所有可用的配置
  switch   NAME          切换到指定的配置
  new      NAME          创建新的配置
  delete   NAME          删除指定的配置
  peek     NAME          查看指定配置内容
  help                   显示此帮助信息

示例:
  python claude_switcher.py list
  python claude_switcher.py switch work
  python claude_switcher.py new home
  python claude_switcher.py delete temp
  python claude_switcher.py peek default

配置文件位置:
  ~/.claude/settings.json
"""


def print_help():
    print(HELP_TEXT)


def main():
    parser = argparse.ArgumentParser(
        description="Claude配置管理工具",
        add_help=True,  # 启用 -h/--help
        usage="python claude_switcher.py <command> [options]"
    )
    subparsers = parser.add_subparsers(title='子命令', dest="command")

    subparsers.add_parser('list', help='列出所有配置')

    switch_p = subparsers.add_parser('switch', help='切换到指定配置')
    switch_p.add_argument('name', help='配置名称')

    new_p = subparsers.add_parser('new', help='创建新配置')
    new_p.add_argument('name', help='新配置名称')

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
    elif args.command == 'delete':
        manager.delete_config(args.name)
    elif args.command == 'peek':
        manager.peek_config(args.name)
    else:
        print_help()


if __name__ == "__main__":
    main()
