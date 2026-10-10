# ClaudeCodeSwitcher

**一个极简的命令行工具，用来管理多套 Claude 配置，并在不同场景之间快速切换。**

## 功能一览

- **多配置并存**：把不同场景（home / work / 临时测试）的 Claude 配置保存在同一个脚本中。
- **一键切换**：`python claude_switcher.py switch work` 会把指定配置写入 `~/.claude/settings.json`。
- **快速预览**：`python claude_switcher.py peek home` 可直接查看配置内容，不写入任何文件。
- **交互式新建**：`python claude_switcher.py new lab` 会打开 `$EDITOR`，编辑后保存即可加入配置列表。
- **编辑已有配置**：`python claude_switcher.py edit work` 可对现有配置进行修改并自动保存。
- **从当前 Claude 文件导入**：`python claude_switcher.py import current` 可把现有的 `~/.claude/settings.json` 导入为一个命名配置。
- **安全删除**：`python claude_switcher.py delete lab` 可删除不再需要的配置；`default` 不允许删除。
- **完善的错误处理**：JSON 验证、编辑取消处理、文件操作异常捕获。
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

4. 编辑已有的配置：

   ```bash
   python claude_switcher.py edit work
   # 编辑器会弹出，修改后保存即可
   ```

5. 如果你已经有一份现成的 Claude 配置，可以直接导入：

   ```bash
   python claude_switcher.py import current
   ```

## 命令速查

| 命令 | 作用 |
|---|---|
| `list` | 列出所有已保存的配置名 |
| `switch NAME` | 把 NAME 配置写入 `~/.claude/settings.json` |
| `peek NAME` | 在终端打印 NAME 配置内容，不保存任何文件 |
| `new NAME` | 用 `$EDITOR` 创建新配置 |
| `edit NAME` | 用 `$EDITOR` 编辑已有配置 |
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

## 特性详解

### 编辑配置（edit 命令）

与 `new` 命令类似，`edit` 命令会打开编辑器，但它：
- 基于现有配置进行编辑（而不是空白配置）
- 自动检测改动：如果保存后配置内容未变化，不会写入文件
- 支持取消操作：关闭编辑器或按下 Ctrl+C 时，原配置保持不变

### 错误处理

脚本内置了完善的错误处理：
- **JSON 格式验证**：确保所有配置都是有效的 JSON
- **文件操作异常**：处理权限不足、磁盘满等问题
- **编辑器异常**：用户取消编辑、编辑器不存在等情况

### 零依赖设计

所有功能仅使用 Python 标准库：
- `json` - 配置序列化
- `subprocess` - 编辑器调用
- `tempfile` - 临时编辑文件
- `pathlib` - 跨平台路径处理

## 开发与贡献

这是一个小而精的 Python 脚本，结构简单，适合二次开发或根据自己的 Claude 配置进行扩展。

```bash
python claude_switcher.py help
```

欢迎提交 PR 或提 Issue。  

License: MIT
