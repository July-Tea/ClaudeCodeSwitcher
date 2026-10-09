# ClaudeCodeSwitcher

**一个极简的命令行工具，用来管理多套 Claude 配置，并在不同场景之间快速切换。**

## 功能一览

- **多配置并存**：把不同场景（home / work / 临时测试）的 Claude 配置保存在同一个脚本中。
- **一键切换**：`python claude_switcher.py switch work` 会把指定配置写入 `~/.claude/settings.json`。
- **快速预览**：`python claude_switcher.py peek home` 可直接查看配置内容，不写入任何文件。
- **交互式新建**：`python claude_switcher.py new lab` 会打开 `$EDITOR`，编辑后保存即可加入配置列表。
- **从当前 Claude 文件导入**：`python claude_switcher.py import current` 可把现有的 `~/.claude/settings.json` 导入为一个命名配置。
- **安全删除**：`python claude_switcher.py delete lab` 可删除不再需要的配置；`default` 不允许删除。
- **零依赖**：仅依赖 Python 标准库，开箱即用。

## 安装

```bash
curl -O https://raw.githubusercontent.com/July-Tea/ClaudeCodeSwitcher/main/claude_switcher.py
```

然后在任意目录运行：

```bash
python claude_switcher.py
```

## 快速开始

1. 首次查看当前配置：

   ```bash
   python claude_switcher.py list
   python claude_switcher.py peek default
   ```

2. 为工作场景新增一套配置：

   ```bash
   python claude_switcher.py new work
   # 编辑器会弹出，按需修改后保存退出
   ```

3. 在不同配置之间切换：

   ```bash
   python claude_switcher.py switch home
   python claude_switcher.py switch work
   ```

4. 如果你已经有一份现成的 Claude 配置，可以直接导入：

   ```bash
   python claude_switcher.py import current
   ```

## 命令速查

| 命令 | 作用 |
|---|---|
| `list` | 列出所有已保存的配置名 |
| `switch NAME` | 把 NAME 配置写入 `~/.claude/settings.json` |
| `peek NAME` | 在终端打印 NAME 配置内容，不保存任何文件 |
| `new NAME` | 用 `$EDITOR` 创建/覆盖 NAME 配置 |
| `import NAME` | 从 `~/.claude/settings.json` 导入配置到管理列表 |
| `delete NAME` | 删除 NAME 配置（`default` 不可删） |
| `help` | 显示完整帮助信息 |

## 配置结构

脚本内部保存的是一个 `CONFIGS` 字典，示例结构如下：

```python
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
```

保存后的 Claude 配置会按同样格式写入：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://sk.xxx.com"
  },
  "permissions": {
    "allow": [],
    "deny": []
  }
}
```

## 开发与贡献

这是一个小而精的 Python 脚本，结构简单，适合二次开发或根据自己的 Claude 配置进行扩展。

```bash
python claude_switcher.py help
```

欢迎提交 PR 或提 Issue。  

License: MIT
