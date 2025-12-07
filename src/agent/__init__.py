"""
Agent package - AI agent implementations using deepagent.

This package provides the PTC (Programmatic Tool Calling) agent pattern:
- Uses deepagent for orchestration and sub-agent delegation
- Integrates Daytona sandbox via DaytonaBackend
- MCP tools accessed through execute_code tool

Structure:
- agent.py: Main PTCAgent using deepagent
- backends/: Custom backends (DaytonaBackend)
- prompts/: Prompt templates (base, research)
- tools/: Custom tools (execute_code, research)
- langchain_tools/: LangChain @tool implementations (Bash, Read, Write, Edit, Glob, Grep)
- subagents/: Sub-agent definitions

Configuration:
- All config classes moved to src/config package
- Programmatic (default): Create AgentConfig directly or use AgentConfig.create()
- File-based: Use load_from_files() from src.config
"""

from .agent import PTCAgent, PTCExecutor, create_ptc_agent
from .backends import DaytonaBackend
from .subagents import create_research_subagent

# Re-export from src.config for backward compatibility
from src.config import (
    # Config classes (pure data)
    AgentConfig,
    LLMConfig,
    LLMDefinition,
    # Config loading
    load_from_files,
    load_core_from_files,
    load_from_dict,
    load_llm_catalog,
    # Config path utilities
    get_default_config_dir,
    get_config_search_paths,
    find_config_file,
    find_project_root,
    ensure_config_dir,
    # Template generation
    generate_config_template,
    # Utilities
    configure_logging,
)

__all__ = [
    # Config classes (pure data)
    "AgentConfig",
    "LLMConfig",
    "LLMDefinition",
    # Config loaders (optional file-based)
    "load_from_files",
    "load_core_from_files",
    "load_from_dict",
    "load_llm_catalog",
    # Config path utilities
    "get_default_config_dir",
    "get_config_search_paths",
    "find_config_file",
    "find_project_root",
    "ensure_config_dir",
    # Template generation
    "generate_config_template",
    # Utilities
    "configure_logging",
    # Agent
    "PTCAgent",
    "PTCExecutor",
    "create_ptc_agent",
    "DaytonaBackend",
    "create_research_subagent",
]
