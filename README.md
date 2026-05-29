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

## FAQ: Common MCP Questions

### 1. MCP Server 是做什么的？它会一直运行吗？

MCP Server 是“给 AI 客户端提供工具的服务”。

在这个项目里，Codex 自己不会直接访问 AI HOT API。Codex 会先启动这个本地
MCP Server，然后询问它：

```text
你有哪些工具？
```

这个 MCP Server 会告诉 Codex：

```text
我有 get_daily 和 get_items
```

当你在 Codex 里说：

```text
调用 aihot 的 get_items，take=5
```

Codex 会通过 MCP 协议请求本地 Server 执行 `get_items`。

这个 stdio MCP Server 通常不是 24 小时运行的公网后端。它更像一个由 Codex
按需启动的本地工具进程：

1. Codex 根据配置启动 `python -m src.server`
2. Server 保持运行，等待 Codex 发工具调用
3. 当前会话结束或客户端关闭时，Server 进程通常也会结束

所以它不是“提供一个 URL 给浏览器访问”的 Web 服务，而是“让 AI 客户端通过
MCP 协议调用的本地工具服务”。

### 2. `FastMCP("aihot-mcp-server")` 初始化了什么？

代码里有这一句：

```python
mcp = FastMCP("aihot-mcp-server")
```

它创建了一个 MCP Server 对象。可以把它理解成：

```text
工具注册中心 + MCP 协议处理器
```

它负责保存 server 名字、保存工具列表、根据函数签名生成 tool schema，并处理
MCP 里的常见请求，例如：

- `initialize`
- `tools/list`
- `tools/call`

但是这一句本身还没有开始读写消息。真正启动通信的是：

```python
mcp.run(transport="stdio")
```

这里明确指定了 `transport="stdio"`，意思是：

```text
从 stdin 读 MCP 请求
往 stdout 写 MCP 响应
```

MCP 的消息格式底层是 JSON-RPC。客户端可能发：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

Server 返回：

```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}
```

所以：

- `FastMCP(...)` 创建 MCP app
- `@mcp.tool()` 注册工具
- `mcp.run(transport="stdio")` 选择 stdio 作为传输方式并开始运行

### 3. MCP tool 是怎么暴露的？它会变成 URL 吗？

不会。MCP tool 不是 URL。

传统 Web 后端常见的是：

```text
GET /api/items
POST /api/search
```

但这个 demo 用的是 stdio MCP Server，没有 HTTP 端口，也没有 `/api/...` 这种给
Codex 访问的 URL。

工具暴露靠的是装饰器：

```python
@mcp.tool()
async def get_daily() -> str:
    ...
```

`@mcp.tool()` 的意思是：

```text
把这个 Python 函数登记到 MCP Server 的工具列表里
```

当 Codex 调用 `tools/list` 时，MCP Server 会返回工具名称、描述和参数结构。

当 Codex 调用 `tools/call` 时，例如：

```json
{
  "name": "get_items",
  "arguments": {
    "take": 5
  }
}
```

`FastMCP` 会找到 Python 函数 `get_items`，把参数传进去执行。

需要区分两段通信：

```text
Codex -> MCP Server: 不是 URL，是 MCP tools/call
MCP Server -> AI HOT: 这里才是 HTTP URL
```

也就是说，MCP tool 本身不是 HTTP API。只是 tool 内部可以再去访问真正的 HTTP
API，比如：

```python
upstream_get("/api/public/items", params=params)
```

### 4. 什么是自动带浏览器 User-Agent？成功和失败结果长什么样？

`User-Agent` 是 HTTP 请求头，用来告诉服务器“我是谁”。

浏览器访问网页时通常会带类似这样的头：

```text
User-Agent: Mozilla/5.0 ... Chrome/124 ...
```

普通 Python 脚本可能默认带：

```text
python-httpx/0.28.1
```

有些网站会拒绝脚本默认 UA。AI HOT 上游可能会对普通脚本 UA 返回 403，所以这个
项目在 `src/http_client.py` 里固定写了一个浏览器 UA：

```python
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
```

发送请求时自动带上：

```python
httpx.AsyncClient(
    headers={"User-Agent": BROWSER_UA},
    timeout=20.0,
)
```

所谓“自动”，意思是调用 `get_daily` 或 `get_items` 的人不用传这个 header。只要
请求经过 `upstream_get()`，就一定会带上。

上游请求结果统一包装成 `UpstreamResult`：

```python
@dataclass
class UpstreamResult:
    ok: bool
    status: int | None
    data: Any = None
    error: str | None = None
```

成功时大致长这样：

```python
UpstreamResult(
    ok=True,
    status=200,
    data={...},
    error=None,
)
```

HTTP 失败时大致长这样：

```python
UpstreamResult(
    ok=False,
    status=403,
    data=None,
    error="Forbidden...",
)
```

网络连接失败时大致长这样：

```python
UpstreamResult(
    ok=False,
    status=None,
    data=None,
    error="All connection attempts failed",
)
```

然后 `server.py` 会把成功结果格式化成 pretty JSON 字符串，把失败结果格式化成
`Error: ...` 字符串返回给 Codex。

### 5. 为什么 stdio 模式下日志不能写 stdout？

这是 stdio MCP Server 最重要的规则之一。

stdio 模式下，MCP Client 和 MCP Server 用标准输入/标准输出通信。可以想象成两根
管子：

```text
Codex -> Server stdin   : Codex 发 MCP 请求
Server stdout -> Codex  : Server 回 MCP 响应
```

Codex 期待 Server 的 stdout 里只有 JSON-RPC 消息，例如：

```json
{"jsonrpc":"2.0","id":1,"result":{"content":[]}}
```

如果你在代码里写：

```python
print("calling upstream...")
```

`print()` 默认写 stdout。于是 stdout 可能变成：

```text
calling upstream...
{"jsonrpc":"2.0","id":1,"result":{"content":[]}}
```

Codex 读取 stdout 时，第一行看到的是：

```text
calling upstream...
```

这不是 JSON-RPC 消息，客户端就可能解析失败，表现为协议错误或 MCP Server 异常。

所以 stdout 必须保持“纯净”，只给 MCP 协议消息使用。

日志应该写 stderr。stderr 是另一根独立管子：

```text
stdout: 给 MCP 协议
stderr: 给人类看日志
```

这个项目的 logger 就是这样写的：

```python
handler = logging.StreamHandler(sys.stderr)
```

一句话总结：

```text
stdio MCP Server 的 stdout 是协议通道，不是日志通道。
```

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
