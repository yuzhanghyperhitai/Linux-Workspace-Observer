# LWO 开发环境指南

## 快速开始（开发模式）

### 1. 配置文件

**方式一：使用项目目录配置文件（推荐）**
```bash
# 项目根目录创建 lwo.toml
cp config/lwo.toml.example lwo.toml

# 编辑配置
vim lwo.toml
```

配置文件读取优先级：
1. 环境变量 `LWO_CONFIG` 指定的路径
2. 项目根目录的 `lwo.toml`（**开发环境自动使用**）
3. `~/.config/lwo/lwo.toml`（生产环境默认）

**方式二：使用环境变量指定配置文件**
```bash
export LWO_CONFIG=/path/to/your/lwo.toml
```

### 2. Shell Hook 测试（无需安装）

**使用开发助手脚本（推荐）**：
```bash
# 在项目根目录执行（会自动加载 shell hook）
source dev.sh

# 现在可以使用便捷命令：
lwo-start    # 启动守护进程
lwo-stop     # 停止守护进程
lwo-report   # 查看报告
lwo-log      # 查看日志
```

**手动加载 Shell Hook**：
```bash
# Zsh 用户
source scripts/shell_hooks/zsh_hook.sh

# Bash 用户
source scripts/shell_hooks/bash_hook.sh
```

**特点**：
- ✅ 仅在当前 Shell 会话有效
- ✅ 不会修改 `~/.zshrc` 或 `~/.bashrc`
- ✅ 关闭终端后自动失效
- ✅ 适合开发测试

### 3. 数据库配置

```bash
# 设置数据库密码
export LWO_DB_PASSWORD="your_password"

# 设置 OpenAI API Key
export OPENAI_API_KEY="sk-..."
```

### 4. 启动开发环境

```bash
# 方式一：使用 dev.sh（推荐）
source dev.sh
lwo-start

# 方式二：手动启动
export LWO_CONFIG=./lwo.toml
source scripts/shell_hooks/zsh_hook.sh  # 或 bash_hook.sh
uv run main.py start
```

### 5. 测试数据采集

```bash
# 执行一些命令测试
ls -la
git status
python --version

# 查看数据库记录
psql -h localhost -U lwo_user -d lwo -c "SELECT command, exit_code FROM shell_commands LIMIT 5;"
```

---

## 开发 vs 生产环境

| 项目 | 开发环境 | 生产环境 |
|------|----------|----------|
| **配置文件** | `./lwo.toml` | `~/.config/lwo/lwo.toml` |
| **Shell Hook** | `source dev.sh` 临时加载 | `bash scripts/install.sh` 永久安装 |
| **数据目录** | `~/.local/share/lwo` | `~/.local/share/lwo` |
| **影响范围** | 当前 Shell 会话 | 所有新 Shell 会话 |

---

## 开发工作流

```bash
# 1. 进入项目目录
cd /home/yuzhang/Hyperhit/lwo

# 2. 激活开发环境
source dev.sh

# 3. 启动守护进程
lwo-start

# 4. 开发和测试...
# (执行命令会被 Shell Hook 捕获)

# 5. 查看日志
lwo-log

# 6. 查看报告
lwo-report

# 7. 停止守护进程
lwo-stop
```

---

## 常见问题

### Q: 为什么不想用 install.sh？
A: `install.sh` 会：
- 修改 `~/.zshrc` 或 `~/.bashrc`（永久安装）
- 创建配置目录 `~/.config/lwo/`
- 创建数据目录 `~/.local/share/lwo/`

开发环境下，我们希望更灵活的控制，不影响系统配置。

### Q: dev.sh 做了什么？
A: `dev.sh` 会：
- 设置 `LWO_CONFIG` 环境变量指向项目根目录的 `lwo.toml`
- 临时加载 Shell Hook（仅当前会话）
- 提供便捷命令别名（`lwo-start`, `lwo-stop` 等）
- **不会**修改任何配置文件

### Q: 如何卸载开发环境？
A: 直接关闭终端即可。所有更改仅在当前 Shell 会话有效。

### Q: 能否同时使用开发和生产环境？
A: 可以，它们使用不同的配置文件路径，互不影响。

---

## 调试技巧

### 查看配置文件加载情况
```python
# 在 Python 中测试
from lwo.config import get_config
config = get_config()
print(f"Config file: {config.config_path}")
```

### 查看 Shell Hook 是否工作
```bash
# 执行一个命令
echo "test"

# 立即查询数据库
psql -h localhost -U lwo_user -d lwo -c \
  "SELECT command, exit_code, created_at FROM shell_commands ORDER BY id DESC LIMIT 1;"
```

### 查看守护进程日志
```bash
tail -f ~/.local/share/lwo/lwo.log
```
