"""Shared configuration loading utilities.

This module provides common functions for loading and validating YAML configuration
files, eliminating duplication between CoreConfig and AgentConfig.
"""

import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import yaml
from dotenv import load_dotenv


async def load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file asynchronously.

    Args:
        file_path: Path to the YAML file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML parsing fails or file is empty
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {file_path}\n"
            f"Please create config.yaml with all required settings."
        )

    try:
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()
        # yaml.safe_load is CPU-bound but fast for config files
        config_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse config.yaml: {e}")

    if not config_data:
        raise ValueError(
            "config.yaml is empty. Please add required configuration sections."
        )

    return config_data


async def load_dotenv_async(env_file: Path | None = None) -> None:
    """Load environment variables from .env file asynchronously.

    Args:
        env_file: Optional path to .env file. If None, searches default locations.
    """
    if env_file:
        await asyncio.to_thread(load_dotenv, env_file)
    else:
        await asyncio.to_thread(load_dotenv)


def validate_required_sections(
    config_data: dict[str, Any],
    required_sections: list[str],
    config_name: str = "config.yaml"
) -> None:
    """Validate that all required sections exist in config data.

    Args:
        config_data: Parsed config dictionary
        required_sections: List of required section names
        config_name: Name of config file for error messages

    Raises:
        ValueError: If any required sections are missing
    """
    missing = [s for s in required_sections if s not in config_data]
    if missing:
        raise ValueError(
            f"Missing required sections in {config_name}: {', '.join(missing)}\n"
            f"Please add these sections to your config.yaml file."
        )


def validate_section_fields(
    section_data: dict[str, Any],
    required_fields: list[str],
    section_name: str
) -> None:
    """Validate that all required fields exist in a config section.

    Args:
        section_data: Section dictionary
        required_fields: List of required field names
        section_name: Name of section for error messages

    Raises:
        ValueError: If any required fields are missing
    """
    missing = [f for f in required_fields if f not in section_data]
    if missing:
        raise ValueError(
            f"Missing required fields in {section_name} section: {', '.join(missing)}"
        )


# Common field requirements for shared config sections
DAYTONA_REQUIRED_FIELDS = [
    "base_url",
    "auto_stop_interval",
    "auto_archive_interval",
    "auto_delete_interval",
    "python_version",
]

SECURITY_REQUIRED_FIELDS = [
    "max_execution_time",
    "max_code_length",
    "max_file_size",
    "enable_code_validation",
    "allowed_imports",
    "blocked_patterns",
]

MCP_REQUIRED_FIELDS = ["servers", "tool_discovery_enabled"]

LOGGING_REQUIRED_FIELDS = ["level", "format", "file"]

FILESYSTEM_REQUIRED_FIELDS = ["allowed_directories"]
