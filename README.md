# Linux Workspace Observer (LWO)

一款运行在 Linux 后台的**无头（Headless）智能助理**。通过采集系统底层信号与开发工具链状态,使用 OpenAI Agent 推理用户的**工作意图**,并输出**结构化简报**。

## 核心功能

### 数据采集
- **Shell Hook**: 捕获命令内容、执行目录、耗时及退出码
- **进程监控**: 每 60s 识别活跃的"重量级"进程（IDE、Docker、编译器）
- **Git 上下文**: 自动检测 Git 仓库,记录分支意图（如 `fix/`, `feat/`）
- **文件监控**: 智能发现项目目录并监控文件变化（基于 inotify）

### 智能分析
- **OpenAI Agent**: 使用 GPT-4o 分析工作状态
- **自动推理**: 识别当前状态（Coding/Debugging/Learning/Idle）
- **智能目录发现**: AI 自动分析并推荐需要监控的项目目录

### 隐私保护
- **敏感信息脱敏**: 自动过滤密码、API Key、邮箱等
- **数据保留策略**: 原始数据保留 7 天,聚合数据保留 30 天

## 架构

```
lwo/
├── collectors/     # 数据采集层
│   ├── shell_hook.py      # Shell 命令捕获
│   ├── process_snapshot.py # 进程监控
│   ├── git_context.py     # Git 上下文
│   └── file_pulse.py      # 文件监控
├── processors/     # 数据处理层
│   ├── sanitizer.py       # 敏感信息脱敏
│   └── aggregator.py      # 事件聚合
├── inference/      # 智能分析层
│   ├── openai_agent.py    # OpenAI Agent 客户端
│   └── analyzer.py        # 状态分析器
├── storage/        # 存储层（PostgreSQL）
│   ├── database.py
│   └── schema.sql
└── cli/            # 交互层
    ├── commands.py
    └── reporter.py
```

## 安装

### 1. 克隆项目
```bash
git clone <repository-url>
cd lwo
```

### 2. 安装依赖
```bash
# 项目使用 uv 管理依赖
uv sync
```

### 3. 配置数据库
```bash
# 创建 PostgreSQL 数据库
createdb lwo
createuser lwo_user

# 设置环境变量
export LWO_DB_PASSWORD="your_password"
export OPENAI_API_KEY="sk-..."
```

### 4. 配置文件
复制配置模板并编辑:
```bash
mkdir -p ~/.config/lwo
cp config/lwo.toml.example ~/.config/lwo/lwo.toml
```

### 5. 安装 Shell Hook
```bash
bash scripts/install.sh
source ~/.zshrc  # 或 ~/.bashrc
```

## 使用

### 启动守护进程
```bash
uv run main.py start
```

### 查看当前工作简报
```bash
uv run main.py report
```

### 生成每日日报
```bash
uv run main.py daily
```

### 停止守护进程
```bash
uv run main.py stop
```

## 配置示例

`~/.config/lwo/lwo.toml`:
```toml
[general]
data_dir = "~/.local/share/lwo"
log_level = "INFO"

[database]
host = "localhost"
port = 5432
name = "lwo"
user = "lwo_user"
password = ""  # 从环境变量 LWO_DB_PASSWORD 读取

[collectors]
process_snapshot_interval = 60
file_watch_extensions = [".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".md"]

[openai]
api_key = ""  # 从环境变量 OPENAI_API_KEY 读取
model = "gpt-4o"
base_url = "https://api.openai.com/v1"

[reporting]
daily_report_time = "18:00"
report_output_dir = "~/lwo-reports"
```

## 非功能特性

- **极低开销**: CPU 占用 < 1%, 内存占用 < 100MB
- **隐私安全**: 敏感信息自动脱敏,支持纯本地模式
- **自动清理**: 每日自动轮转清理历史数据
- **智能适应**: AI 自动学习用户工作模式,动态调整监控策略

## 开发

### 运行测试
```bash
uv add --dev pytest pytest-cov
uv run pytest tests/ -v --cov=lwo
```

### 架构文档
详细设计文档请查看:
- [实现计划](docs/implementation_plan.md)
- [架构说明](docs/architecture_notes.md)

## License

MIT
