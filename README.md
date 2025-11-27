# Open PTC Agent

[Getting Started](#getting-started) | [Configuration](docs/CONFIGURATION.md)

## What is Programmatic Tool Calling?

This project is an open source implementation of Anthropic recently introduced [Programmatic Tool Calling (PTC)](https://www.anthropic.com/engineering/advanced-tool-use), which enables agents to invoke tools with code execution rather than making individual JSON tool calls. This paradigm is also featured in their earlier engineering blog [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp).
## Why PTC?

1. LLMs are exceptionally good at writing code! They excel at understanding context, reasoning about data flows, and generating precise logic. PTC lets them do what they do best - write code that orchestrates entire workflows rather than reasoning through one tool call at a time.

2. Traditional tool calling returns full results to the model's context window. Analyzing expenses for 20 employees means 2,000+ line items polluting context - over 110,000 tokens just to produce a summary. With PTC, code runs in a sandbox, processes data locally, and only the final output returns to the model. Result: 85-98% token reduction.

3. PTC particularly shines when working with large volumes of structured data, time series data (like financial market data), and scenarios requiring further data processing - filtering, aggregating, transforming, or visualizing results before returning them to the model.

## How It Works
This project is implementing based on [deep-agent](https://github.com/langchain-ai/deepagents) from langchain-ai and [daytona](https://www.daytona.io/) for sandbox environment.

```
User Task
    |
    v
+-------------------+
|    PTCAgent       |  Tool discovery -> Writes Python code
+-------------------+
    |       ^
    v       |
+-------------------+
|  Daytona Sandbox  |  Executes code
|  +-------------+  |
|  | MCP Tools   |  |  tool() -> process / filter / aggregate -> dump to data/ directory
|  | (Python)    |  |
|  +-------------+  |
+-------------------+
    |
    v
+-------------------+
|Final deliverables |  Files and data can be downloaded from sandbox
+-------------------+
```
## Features

- **Universal MCP Support** - Auto-converts any MCP server tools to Python functions
- **Progressive Tool Discovery** - Tools discovered on-demand; avoids large number of tokens of upfront tool definitions
- **Custom MCP Upload** - Deploy Python MCP implementations directly into sandbox sessions
- **Enhanced File Tools** - Refined glob, grep and other file operation tools based on LangChain DeepAgent
- **Daytona Backend** - Secure code execution with filesystem isolation and snapshot support
- **Auto Image Upload** - Charts and images auto-uploaded to cloud storage (Cloudflare R2, AWS S3, Alibaba OSS)
- **LangGraph Ready** - Compatible with LangGraph Cloud/Studio deployment
- **Multi-LLM Support** - Works with Anthropic, OpenAI, and Any LLM provider you configure in `llms.json`

## Project Structure

```
├── src/
│   ├── ptc_core/              # Core infrastructure
│   │   ├── sandbox.py         # PTCSandbox (glob, grep, read, write)
│   │   ├── mcp_registry.py    # MCP server discovery & connection
│   │   ├── tool_generator.py  # MCP schema → Python functions
│   │   ├── session.py         # Session lifecycle management
│   │   └── config.py          # Configuration classes
│   │
│   └── agent/                 # Agent implementation
│       ├── agent.py           # PTCAgent, PTCExecutor
│       ├── config.py          # AgentConfig
│       ├── tools/             # Native tool implementations
│       ├── prompts/           # Jinja2 templates
│       ├── subagents/         # Research & general subagents
│       └── backends/          # DaytonaBackend
│
├── mcp_servers/               # Custom MCP server implementations for demo purposes
│   ├── yfinance_mcp_server.py
│   └── tickertick_mcp_server.py
│
├── config.yaml                # Main configuration
├── llms.json                  # LLM provider definitions
└── PTC_Agent.ipynb            # Demo notebook
```

## Native Tools

The agent has access to 7 native tools plus some built-in middleware capabilities from [deep-agent](https://github.com/langchain-ai/deepagents):

### Core Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| **execute_code** | Execute Python with MCP tool access | `code` |
| **Bash** | Run shell commands | `command`, `timeout`, `working_dir` |
| **Read** | Read file with line numbers | `file_path`, `offset`, `limit` |
| **Write** | Write/overwrite file | `file_path`, `content` |
| **Edit** | Exact string replacement | `file_path`, `old_string`, `new_string` |
| **Glob** | File pattern matching | `pattern`, `path` |
| **Grep** | Content search (ripgrep) | `pattern`, `path`, `output_mode` |

### Middleware (via langchain/deep-agent)

| Middleware | Description | Tools Provided |
|------------|-------------|----------------|
| **SubagentsMiddleware** | Delegates specialized tasks to sub-agents with isolated execution | `task()` |
| **FilesystemMiddleware** | File operations | `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `ls`, `bash` |
| **TodoListMiddleware** | Task planning and progress tracking (auto-enabled) | `write_todos` |
| **SummarizationMiddleware** | Auto-summarizes conversation history (auto-enabled) | - |

**Available Subagents:**
- `research` - Web search with Tavily + think tool for strategic reflection
- `general` - General purpose with full execute_code and filesystem access

Note: For better tool discovery, I override the built-in filesystem middleware from langchain deep-agent. You can disable it by setting `use_custom_filesystem_tools` to false in `config.yaml`.

## MCP Integration

### Demo MCP Servers

The demo includes 3 enabled MCP servers configured in `config.yaml`:

| Server | Transport | Tools | Purpose |
|--------|-----------|-------|---------|
| **tavily** | stdio (npx) | 4 | Web search |
| **yfinance** | stdio (python) | 10 | Stock prices, financials |
| **tickertick** | stdio (python) | 7 | Financial news |

### How MCP Tools Appear

**In Prompts** - Tool summaries are injected into the system prompt:
```
tavily: Web search engine for finding current information
  - Module: tools/tavily.py
  - Tools: 4 tools available
  - Import: from tools.tavily import <tool_name>
```

**In Sandbox** - Full Python modules are generated:
```
/home/daytona/
├── tools/
│   ├── mcp_client.py      # MCP communication layer
│   ├── tavily.py          # from tools.tavily import search
│   ├── yfinance.py        # from tools.yfinance import get_stock_history
│   └── docs/              # Auto-generated documentation
│       ├── tavily/*.md
│       └── yfinance/*.md
├── results/               # Agent output
└── data/                  # Input data
```

**In Code** - Agent imports and uses tools directly:
```python
from tools.yfinance import get_stock_history
import pandas as pd

# Fetch data - stays in sandbox
history = get_stock_history(ticker="AAPL", period="1y")

# Process locally - no tokens wasted
df = pd.DataFrame(history)
summary = {"mean": df["close"].mean(), "volatility": df["close"].std()}

# Only summary returns to model
print(summary)
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js (for MCP servers)
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/Chen-zexi/open-ptc-agent.git
cd open-ptc-agent
uv sync
```

### Minimal Configuration

Create a `.env` file with the minimum required keys:

```bash
# One LLM provider (choose one)
ANTHROPIC_API_KEY=your-key
# or
OPENAI_API_KEY=your-key
# or
# Any model you configred in llms.json and config.yaml

# Daytona (required)
DAYTONA_API_KEY=your-key
```
Get your Daytona API key from [Daytona Dashboard](https://app.daytona.io/dashboard/keys). They provide free credits for new users!

### Extended Configuration

For full functionality, add optional keys:

```bash
# MCP Servers
TAVILY_API_KEY=your-key          # Web search
ALPHA_VANTAGE_API_KEY=your-key   # Financial data

# Cloud Storage (choose one provider)
R2_ACCESS_KEY_ID=...             # Cloudflare R2
AWS_ACCESS_KEY_ID=...            # AWS S3
OSS_ACCESS_KEY_ID=...            # Alibaba OSS

# Tracing (optional)
LANGSMITH_API_KEY=your-key
```

See `.env.example` for the complete list of configuration options.

### Demo Notebooks

Quick start with the jupyter notebook:

- **PTC_Agent.ipynb** - Quick demo with open-ptc-agent

Optionally, you can use the langgraph api to deploy the agent.

## Configuration

The project uses two configuration files:

- **config.yaml** - Main configuration (LLM selection, MCP servers, Daytona, security, storage)
- **llms.json** - LLM provider definitions

### Quick Config

Select your LLM in `config.yaml`:

```yaml
llm:
  name: "claude-sonnet-4-5"  # Options: claude-sonnet-4-5, gpt-5.1-codex-mini, gemini-3-pro
```

Enable/disable MCP servers:

```yaml
mcp:
  servers:
    - name: "tavily"
      enabled: true  # Set to false to disable
```

For complete configuration options including Daytona settings, security policies, and adding custom LLM providers, see the [Configuration Guide](docs/CONFIGURATION.md).

## Acknowledgements

This project builds on research and tools from:

**Research/Articles**

- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use) - Anthropic
- [Code execution with MCP: building more efficient AI agents](https://www.anthropic.com/engineering/code-execution-with-mcp) - Anthropic
- [CodeAct: Executable Code Actions Elicit Better LLM Agents](https://arxiv.org/abs/2402.01030) - Wang et al.

**Frameworks and Infrastructure**

- [LangChain DeepAgent](https://github.com/langchain-ai/deep-agent) - Base Agent Framework
- [Daytona](https://www.daytona.io/) - Sandbox infrastructure

## License

MIT License
