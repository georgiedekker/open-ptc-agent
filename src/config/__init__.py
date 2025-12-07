"""Unified configuration package for Open PTC Agent.

This package consolidates all configuration-related code:
- core.py: Core infrastructure configs (Daytona, MCP, Filesystem, Security, Logging)
- agent.py: Agent-specific configs (AgentConfig, LLMConfig, LLMDefinition)
- loaders.py: File-based configuration loading
- utils.py: Shared utilities for config parsing

Usage:
    # Programmatic configuration (recommended)
    from langchain_anthropic import ChatAnthropic
    from src.config import AgentConfig

    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    config = AgentConfig.create(llm=llm)

    # File-based configuration (for CLI, etc.)
    from src.config import load_from_files
    config = await load_from_files()

    # Core config only (for SessionManager)
    from src.config import load_core_from_files
    core_config = await load_core_from_files()
"""

# Core data classes
from src.config.core import (
    CoreConfig,
    DaytonaConfig,
    FilesystemConfig,
    LoggingConfig,
    MCPConfig,
    MCPServerConfig,
    SecurityConfig,
)

# Agent data classes
from src.config.agent import (
    AgentConfig,
    LLMConfig,
    LLMDefinition,
)

# File-based loading
from src.config.loaders import (
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
)

# Utilities
from src.config.utils import configure_logging

__all__ = [
    # Core data classes
    "CoreConfig",
    "DaytonaConfig",
    "FilesystemConfig",
    "LoggingConfig",
    "MCPConfig",
    "MCPServerConfig",
    "SecurityConfig",
    # Agent data classes
    "AgentConfig",
    "LLMConfig",
    "LLMDefinition",
    # Config loading
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
]
