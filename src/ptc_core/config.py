"""Configuration management for Open PTC Agent core infrastructure.

This module loads core configuration from config.yaml:
- Daytona sandbox settings
- MCP server configurations
- Filesystem access settings
- Security settings
- Logging settings

Credentials are loaded from .env file.
LLM configuration is handled separately in src/agent/config.py.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.utils.config_loader import (
    DAYTONA_REQUIRED_FIELDS,
    FILESYSTEM_REQUIRED_FIELDS,
    LOGGING_REQUIRED_FIELDS,
    MCP_REQUIRED_FIELDS,
    SECURITY_REQUIRED_FIELDS,
    load_dotenv_async,
    load_yaml_file,
    validate_required_sections,
    validate_section_fields,
)


class DaytonaConfig(BaseModel):
    """Daytona sandbox configuration."""

    api_key: str  # Loaded from .env
    base_url: str  # From config.yaml
    auto_stop_interval: int  # From config.yaml
    auto_archive_interval: int  # From config.yaml
    auto_delete_interval: int  # From config.yaml
    python_version: str  # From config.yaml

    # Snapshot configuration for faster sandbox initialization
    snapshot_enabled: bool = True  # From config.yaml (optional, default: True)
    snapshot_name: Optional[str] = None  # From config.yaml (optional)
    snapshot_auto_create: bool = True  # From config.yaml (optional, default: True)


class SecurityConfig(BaseModel):
    """Security configuration for code execution."""

    max_execution_time: int  # From config.yaml
    max_code_length: int  # From config.yaml
    max_file_size: int  # From config.yaml
    enable_code_validation: bool  # From config.yaml
    allowed_imports: List[str]  # From config.yaml
    blocked_patterns: List[str]  # From config.yaml


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str
    enabled: bool = True  # Whether this server is enabled (default: True)
    description: str = ""  # What the MCP server does
    instruction: str = ""  # When/how to use this server
    transport: Literal["stdio", "sse", "http"] = "stdio"
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None  # For SSE/HTTP transports
    tool_exposure_mode: Optional[Literal["summary", "detailed"]] = None  # Per-server override


class MCPConfig(BaseModel):
    """MCP server configurations."""

    servers: List[MCPServerConfig]  # From config.yaml
    tool_discovery_enabled: bool  # From config.yaml
    lazy_load: Optional[bool] = True  # From config.yaml (optional)
    cache_duration: Optional[int] = None  # From config.yaml (optional)
    tool_exposure_mode: Literal["summary", "detailed"] = "summary"  # From config.yaml (optional)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str  # From config.yaml
    format: str  # From config.yaml
    file: str  # From config.yaml


class FilesystemConfig(BaseModel):
    """Filesystem access configuration for first-class filesystem tools."""

    working_directory: str = "/home/daytona"  # Root for virtual path normalization
    allowed_directories: List[str]  # From config.yaml
    enable_path_validation: bool = True  # From config.yaml (optional, default: True)


class CoreConfig(BaseModel):
    """Core infrastructure configuration.

    Contains settings for sandbox, MCP servers, filesystem, security, and logging.
    LLM configuration is handled separately in src/agent/config.py.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Sub-configurations
    daytona: DaytonaConfig
    security: SecurityConfig
    mcp: MCPConfig
    logging: LoggingConfig
    filesystem: FilesystemConfig

    @classmethod
    async def load(
        cls,
        config_file: Optional[Path] = None,
        env_file: Optional[Path] = None,
    ) -> "CoreConfig":
        """Load core configuration from config.yaml and credentials from .env.

        Uses aiofiles for non-blocking I/O. Call with `await CoreConfig.load()`.

        Args:
            config_file: Optional path to config.yaml file (default: ./config.yaml)
            env_file: Optional path to .env file (default: ./.env)

        Returns:
            Configured CoreConfig instance

        Raises:
            FileNotFoundError: If config.yaml is not found
            ValueError: If required configuration is missing or invalid
            KeyError: If required fields are missing from config files
        """
        # Determine file paths
        if config_file is None:
            cwd = await asyncio.to_thread(Path.cwd)
            config_file = cwd / "config.yaml"

        # Load environment variables for credentials
        await load_dotenv_async(env_file)

        # Load config.yaml asynchronously
        config_data = await load_yaml_file(config_file)

        # Validate that all required sections exist in config.yaml
        required_sections = ["daytona", "security", "mcp", "logging", "filesystem"]
        validate_required_sections(config_data, required_sections)

        # Load Daytona configuration
        daytona_data = config_data["daytona"]
        validate_section_fields(daytona_data, DAYTONA_REQUIRED_FIELDS, "daytona")

        # Load snapshot configuration
        daytona_config = DaytonaConfig(
            api_key=os.getenv("DAYTONA_API_KEY", ""),
            base_url=daytona_data["base_url"],
            auto_stop_interval=daytona_data["auto_stop_interval"],
            auto_archive_interval=daytona_data["auto_archive_interval"],
            auto_delete_interval=daytona_data["auto_delete_interval"],
            python_version=daytona_data["python_version"],
            snapshot_enabled=daytona_data.get("snapshot_enabled", True),
            snapshot_name=daytona_data.get("snapshot_name"),
            snapshot_auto_create=daytona_data.get("snapshot_auto_create", True),
        )

        # Load Security configuration
        security_data = config_data["security"]
        validate_section_fields(security_data, SECURITY_REQUIRED_FIELDS, "security")

        security_config = SecurityConfig(
            max_execution_time=security_data["max_execution_time"],
            max_code_length=security_data["max_code_length"],
            max_file_size=security_data["max_file_size"],
            enable_code_validation=security_data["enable_code_validation"],
            allowed_imports=security_data["allowed_imports"],
            blocked_patterns=security_data["blocked_patterns"],
        )

        # Load MCP configuration
        mcp_data = config_data["mcp"]
        validate_section_fields(mcp_data, MCP_REQUIRED_FIELDS, "mcp")

        mcp_servers = [MCPServerConfig(**server) for server in mcp_data["servers"]]
        mcp_config = MCPConfig(
            servers=mcp_servers,
            tool_discovery_enabled=mcp_data["tool_discovery_enabled"],
            lazy_load=mcp_data.get("lazy_load", True),
            cache_duration=mcp_data.get("cache_duration"),
            tool_exposure_mode=mcp_data.get("tool_exposure_mode", "summary"),
        )

        # Load Logging configuration
        logging_data = config_data["logging"]
        validate_section_fields(logging_data, LOGGING_REQUIRED_FIELDS, "logging")

        logging_config = LoggingConfig(
            level=logging_data["level"],
            format=logging_data["format"],
            file=logging_data["file"],
        )

        # Load Filesystem configuration
        filesystem_data = config_data["filesystem"]
        required_filesystem_fields = ["allowed_directories"]
        missing_filesystem = [
            f for f in required_filesystem_fields if f not in filesystem_data
        ]
        if missing_filesystem:
            raise ValueError(
                f"Missing required fields in filesystem section: {', '.join(missing_filesystem)}"
            )

        filesystem_config = FilesystemConfig(
            allowed_directories=filesystem_data["allowed_directories"],
            enable_path_validation=filesystem_data.get("enable_path_validation", True),
        )

        # Create config object
        config = cls(
            daytona=daytona_config,
            security=security_config,
            mcp=mcp_config,
            logging=logging_config,
            filesystem=filesystem_config,
        )

        return config

    def validate_api_keys(self) -> None:
        """Validate that required API keys are present.

        Raises:
            ValueError: If required API keys are missing
        """
        missing_keys = []

        if not self.daytona.api_key:
            missing_keys.append("DAYTONA_API_KEY")

        if missing_keys:
            raise ValueError(
                f"Missing required credentials in .env file:\n"
                f"  - {chr(10).join(missing_keys)}\n"
                f"Please add these credentials to your .env file."
            )
