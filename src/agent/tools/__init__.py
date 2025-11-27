"""
Open PTC Agent Tools Package.

This package contains all tools available to the PTC agent, organized by category:
- code_execution: Tools for executing Python code in the sandbox (OSS-enabled)
- bash: Tools for executing bash commands in the sandbox
- filesystem: Tools for file and directory operations
- search: Tools for file pattern matching and content search
- research: Tools for web search and reasoning

Note: With deepagent, most filesystem tools (ls, read_file, write_file, edit_file,
glob, grep) are provided by the FilesystemMiddleware. These LangChain tool wrappers
are available for alternative agent configurations.
"""

from typing import Any, List

from langchain_core.tools import BaseTool

from .code_execution import create_execute_code_tool
from .bash import create_execute_bash_tool
from .filesystem import create_filesystem_tools
from .search import (
    create_glob_tool,
    create_grep_tool,
)
from .research import tavily_search, think_tool

__all__ = [
    # Code execution
    "create_execute_code_tool",
    # Bash
    "create_execute_bash_tool",
    # Filesystem
    "create_filesystem_tools",
    # Search
    "create_glob_tool",
    "create_grep_tool",
    # Research
    "tavily_search",
    "think_tool",
    # Helper
    "get_all_tools",
]


def get_all_tools(sandbox: Any, mcp_registry: Any) -> List[BaseTool]:
    """Create and return all available tools for the PTC agent.

    Args:
        sandbox: PTCSandbox instance for code execution and file operations
        mcp_registry: MCPRegistry instance for MCP tool access

    Returns:
        List of all configured tools ready for use by the agent
    """
    # Create filesystem tools
    read_file, write_file, edit_file = create_filesystem_tools(sandbox)

    tools = [
        # Code execution tool (primary tool for complex operations)
        create_execute_code_tool(sandbox, mcp_registry),
        # Bash execution tool (for system commands and shell utilities)
        create_execute_bash_tool(sandbox),
        # File operation tools
        read_file,
        write_file,
        edit_file,
        # Search tools (file-based)
        create_glob_tool(sandbox),
        create_grep_tool(sandbox),
    ]

    return tools
