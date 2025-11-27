"""Glob tool for file pattern matching."""

import asyncio
from typing import Any, Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


def create_glob_tool(sandbox: Any):
    """Factory function to create Glob tool.

    Args:
        sandbox: PTCSandbox instance

    Returns:
        Configured Glob tool function
    """

    @tool
    async def glob(pattern: str, path: Optional[str] = None) -> str:
        """Fast file pattern matching tool for finding files by name patterns.

        Works with any codebase size. Supports glob patterns like "**/*.js", "src/**/*.ts", "*.py".
        Returns matching file paths sorted by modification time.

        Use this tool when you need to find files by name patterns. For content-based searches,
        use the Grep tool instead.

        Args:
            pattern: Glob pattern to match files against
                    Examples: "**/*.py", "src/**/*.ts", "*.{js,ts}", "**/test_*.py"
            path: Optional directory to search in (defaults to current working directory if not specified).
                  IMPORTANT: Omit this parameter for default directory - don't enter "undefined" or "null"

        Returns:
            Matching file paths sorted by modification time, or error message if operation failed.

        Pattern Syntax:
            *       - Match anything except /
            **      - Match zero or more directories
            ?       - Match single character
            [...]   - Match character range
            {a,b}   - Match either pattern

        Examples:
            Find all Python files recursively:
            pattern = "**/*.py"

            Find all TypeScript files in src directory:
            pattern = "src/**/*.ts"
            path = "."

            Find all config files:
            pattern = "**/*.{yaml,yml,json}"

            Find test files:
            pattern = "**/test_*.py"
        """
        try:
            # Normalize virtual path to absolute sandbox path
            search_path = path if path is not None else "."
            normalized_path = sandbox.normalize_path(search_path)

            logger.info("Globbing files", pattern=pattern, path=search_path, normalized_path=normalized_path)

            # Validate normalized path
            if sandbox.config.filesystem.enable_path_validation and not sandbox.validate_path(normalized_path):
                error_msg = f"Access denied: {search_path} is not in allowed directories"
                logger.error(error_msg, path=search_path)
                return f"ERROR: {error_msg}"

            # Search for files matching the pattern using normalized path
            matches = await asyncio.to_thread(sandbox.glob_files, pattern, normalized_path)

            if not matches:
                logger.info("No files found", pattern=pattern, path=search_path)
                return f"No files matching pattern '{pattern}' found in '{search_path}'"

            # Virtualize paths in output (strip /home/daytona prefix)
            virtual_matches = [sandbox.virtualize_path(m) for m in matches]

            # Format output with virtual paths
            result = f"Found {len(virtual_matches)} file(s) matching '{pattern}':\n"
            for match in virtual_matches:
                result += f"{match}\n"

            logger.info(
                "Glob completed successfully",
                pattern=pattern,
                path=search_path,
                matches=len(virtual_matches),
            )

            return result.rstrip()

        except Exception as e:
            error_msg = f"Failed to glob files: {str(e)}"
            logger.error(error_msg, pattern=pattern, path=search_path, error=str(e), exc_info=True)
            return f"ERROR: {error_msg}"

    return glob
