# AI HOT MCP Server Demo

一个用于学习 MCP（Model Context Protocol）的轻量 Python demo。

这个项目把 [AI HOT](https://aihot.virxact.com) 的公开 REST API 包装成本地 MCP
Server，让 Codex 或其他 MCP Client 可以通过工具调用查询 AI 资讯。

项目刻意保持小而清楚：不做完整产品，不做复杂测试矩阵，只保留搭建 MCP
Server 时最关键的几个组件。

## What You Will Learn

通过这个 demo，你可以看到：

- MCP Server 如何用 stdio 和客户端通信
- 如何用 Python MCP SDK 的 `FastMCP` 注册工具
- MCP tool 的参数如何由函数签名描述
- tool 内部如何调用外部 REST API
- 为什么 MCP Server 的日志必须写到 stderr
- 如何把本地 MCP Server 配给 Codex

## Project Structure

```text
mcp-demo/
├─ src/
│  ├─ server.py          # MCP Server 入口，注册 tools
│  ├─ http_client.py     # 访问 AI HOT 上游 API
│  ├─ logger.py          # stderr logger
│  └─ __init__.py
├─ tests/
│  └─ unit/
│     └─ test_logger.py
├─ codex-mcp-config.json # JSON 风格 MCP 配置示例
├─ pyproject.toml        # Python 项目和依赖配置
└─ README.md
```

## Key Components

### 1. MCP Server: `src/server.py`

`server.py` 是整个 MCP Server 的入口：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("aihot-mcp-server")
```

`FastMCP` 负责 MCP 协议细节，包括：

- `initialize`
- `tools/list`
- `tools/call`
- stdio JSON-RPC 消息读写

demo 代码不手写 JSON-RPC。我们只关心注册工具。

### 2. MCP Tools

工具通过 `@mcp.tool()` 注册：

```python
@mcp.tool()
async def get_daily() -> str:
    ...
```

这个 demo 暴露两个工具。

#### `get_daily`

获取最新 AI HOT 日报。

参数：无。

内部调用：

```text
GET https://aihot.virxact.com/api/public/daily
```

#### `get_items`

查询 AI HOT 动态条目。

参数：

- `mode`: `selected` 或 `all`，默认 `selected`
- `category`: 可选分类，例如 `ai-models`、`ai-products`、`industry`、`paper`、`tip`
- `take`: 返回数量，默认 `10`，范围 `1..100`
- `q`: 可选关键词

内部调用：

```text
GET https://aihot.virxact.com/api/public/items
```

### 3. HTTP Client: `src/http_client.py`

所有上游 API 请求都集中在 `upstream_get()` 里。

它做三件事：

- 拼接 AI HOT API 地址
- 自动带浏览器 `User-Agent`
- 把成功 JSON 或失败状态包装成统一结果

AI HOT 上游对普通脚本 UA 可能返回 403，所以这里固定注入浏览器 UA：

```python
headers={"User-Agent": BROWSER_UA}
```

### 4. Logger: `src/logger.py`

MCP stdio transport 使用 stdout 传输协议消息，所以日志不能写 stdout。

这个 demo 的 logger 只写 stderr：

```python
handler = logging.StreamHandler(sys.stderr)
```

这点很关键。否则日志会污染 JSON-RPC 消息流，导致 MCP Client 解析失败。

## Install

建议使用 Python 3.10+。

```bash
pip install -e ".[test]"
```

如果只运行 demo，不跑测试：

```bash
pip install -e .
```

## Run Manually

```bash
python -m src.server
```

注意：这是 stdio MCP Server，不是 HTTP 服务。

直接运行时，它会等待 MCP Client 通过 stdin/stdout 发送 JSON-RPC 消息，所以不会打印
`localhost` URL。

## Configure Codex

Codex 的 MCP 配置通常在：

```text
~/.codex/config.toml
```

Windows 示例：

```toml
[mcp_servers.aihot]
command = 'D:\miniforge\python.exe'
args = ["-m", "src.server"]
cwd = 'D:\Projects\Personal\mcp-demo'
```

如果你的 Python 不在 `D:\miniforge\python.exe`，可以用下面命令查看：

```bash
python -c "import sys; print(sys.executable)"
```

然后把 `command` 改成对应路径。

配置完成后，重启 Codex 或开启一个新会话。

## Example Prompts In Codex

查看最近精选 AI 动态：

```text
调用 aihot 的 get_items，take=5
```

查看最新日报：

```text
调用 aihot 的 get_daily
```

查看论文类资讯：

```text
调用 aihot 的 get_items，category=paper，take=5
```

关键词搜索：

```text
调用 aihot 的 get_items，q=OpenAI，take=5
```

## How The Call Flow Works

一次 `get_items` 调用大致是这样：

```text
Codex
  -> MCP tools/call
  -> local Python process: src.server
  -> get_items(...)
  -> upstream_get("/api/public/items", params)
  -> https://aihot.virxact.com/api/public/items
  -> JSON response
  -> pretty JSON string back to Codex
```

MCP Client 不直接访问 AI HOT。它只调用本地 MCP Server 暴露的工具。

## Development

运行测试：

```bash
python -m pytest
```

当前测试只覆盖 logger，因为这个 demo 的重点是先跑通 MCP 基础链路。

## What Is Intentionally Not Included

为了保持 demo 轻量，当前没有加入：

- 完整 Pydantic response models
- property-based tests
- 覆盖率门槛
- 自定义 JSON-RPC 协议层
- 重试、缓存、限流
- 所有 AI HOT API endpoint

这些都可以在理解基础链路后逐步补上。
