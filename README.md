# ClaudeCodeSwitcher

**一个极简的命令行工具，帮你轻松管理多套 Claude 配置。**

## 功能一览

- **多配置并存**：把不同场景（home / work / 临时测试）的 Claude 配置都保存在同一个文件里。
- **一键切换**：`claude_switcher.py switch work` 立即把指定配置写到 `~/.claude/settings.json`。
- **快速预览**：`claude_switcher.py peek home` 查看配置内容，不改动任何文件。
- **交互式新建**：`claude_switcher.py new lab` 打开 `$EDITOR` 直接编辑，保存即生效。
- **安全删除**：`claude_switcher.py delete lab` 删除不再需要的配置（默认配置不可删）。
- **零依赖**：仅用 Python 标准库，开箱即用。

## 安装

```bash
# 克隆或下载 claude_switcher.py.py 到任意目录
curl -O https://raw.githubusercontent.com/July-Tea/ClaudeCodeSwitcher/main/claude_switcher.py
```

## 快速开始

1. 首次运行：
   ```bash
   python claude_switcher.py list        # 查看当前只有 default
   python claude_switcher.py peek default
   ```
2. 为工作场景新建一套配置：
   ```bash
   python claude_switcher.py new work
   # 编辑器会弹出，按需修改后保存退出
   ```
3. 在 home 和 work 之间切换：
   ```bash
   python claude_switcher.py switch home
   python claude_switcher.py switch work
   ```

## 命令速查

| 命令 | 作用 |
|---|---|
| `list` | 列出所有已保存的配置名 |
| `switch NAME` | 把 NAME 配置写入 `~/.claude/settings.json` |
| `peek NAME` | 在终端打印 NAME 配置内容（不保存） |
| `new NAME` | 用 `$EDITOR` 新建/覆盖 NAME 配置 |
| `delete NAME` | 删除 NAME 配置（default 不可删） |
| `help` | 显示完整帮助信息 |

## 开发与贡献

代码短小清晰，欢迎 PR 或提 Issue。  

```bash
python claude_switcher.py.py --help
```

License: MIT
