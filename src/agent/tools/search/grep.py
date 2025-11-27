"""Grep tool for content searching with ripgrep."""

import asyncio
from typing import Any, Literal, Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


def create_grep_tool(sandbox: Any):
    """Factory function to create Grep tool.

    Args:
        sandbox: PTCSandbox instance

    Returns:
        Configured Grep tool function
    """

    @tool
    async def grep(
        pattern: str,
        path: Optional[str] = None,
        output_mode: Optional[Literal["files_with_matches", "content", "count"]] = "files_with_matches",
        glob: Optional[str] = None,
        type: Optional[str] = None,
        i: Optional[bool] = False,
        n: Optional[bool] = True,
        A: Optional[int] = None,
        B: Optional[int] = None,
        C: Optional[int] = None,
        multiline: Optional[bool] = False,
        head_limit: Optional[int] = None,
        offset: int = 0,
    ) -> str:
        """Search for patterns in files using ripgrep.

        ALWAYS use Grep for search tasks. NEVER invoke `grep` or `rg` via Bash command.
        This tool has been optimized for correct permissions and access.

        Supports full regex syntax, file filtering, and multiple output modes.

        Args:
            pattern: Regex pattern to search for
            path: Directory or file to search in (default: ".")
            output_mode: "content", "files_with_matches", or "count"
            glob: File pattern filter (e.g., "*.py")
            type: File type filter (e.g., "py", "js")
            i: Case insensitive search (alias: case_insensitive)
            n: Show line numbers (alias: show_line_numbers)
            A: Lines after match (alias: lines_after)
            B: Lines before match (alias: lines_before)
            C: Lines of context (alias: lines_context)
            multiline: Enable multiline mode where . matches newlines (default: False)
            head_limit: Limit output to first N lines/entries (default: None for unlimited)
            offset: Skip first N lines/entries before applying head_limit (default: 0)

        Returns:
            Search results in the specified format, or error message if operation failed.

        Pattern Syntax (Regex):
            .       - Any character
            .*      - Zero or more of any character
            \\s     - Whitespace
            \\w     - Word character
            \\d     - Digit
            [...]   - Character class
            \\{     - Literal brace (escaped for ripgrep)

        Examples:
            Find files containing "PTCAgent":
            pattern = "PTCAgent"

            Find with file content:
            pattern = "PTCAgent"
            output_mode = "content"

            Case-insensitive search:
            pattern = "error"
            output_mode = "content"
            i = True

            Search only Python files:
            pattern = "async def"
            type = "py"
            output_mode = "content"

            Search with glob pattern:
            pattern = "import.*mcp"
            glob = "*.py"
            output_mode = "content"

            Search with context lines:
            pattern = "class.*Agent"
            output_mode = "content"
            C = 3

            Multiline search:
            pattern = "class.*\\{[\\s\\S]*?def.*init"
            multiline = True
            output_mode = "content"

            Count occurrences:
            pattern = "TODO"
            output_mode = "count"
        """
        try:
            # Normalize virtual path to absolute sandbox path
            search_path = path if path is not None else "."
            normalized_path = sandbox.normalize_path(search_path)

            logger.info(
                "Grepping content",
                pattern=pattern,
                path=search_path,
                normalized_path=normalized_path,
                output_mode=output_mode,
                glob=glob,
                type=type,
                case_insensitive=i,
            )

            # Validate normalized path
            if sandbox.config.filesystem.enable_path_validation and not sandbox.validate_path(normalized_path):
                error_msg = f"Access denied: {search_path} is not in allowed directories"
                logger.error(error_msg, path=search_path)
                return f"ERROR: {error_msg}"

            # Build grep options with normalized path
            options = {
                "pattern": pattern,
                "path": normalized_path,
                "output_mode": output_mode,
                "glob": glob,
                "type": type,
                "case_insensitive": i,
                "show_line_numbers": n,
                "lines_after": A,
                "lines_before": B,
                "lines_context": C,
                "multiline": multiline,
                "head_limit": head_limit,
                "offset": offset,
            }

            # Search for content matching the pattern
            results = await asyncio.to_thread(sandbox.grep_content, **options)

            if not results:
                logger.info("No matches found", pattern=pattern, path=search_path)
                return f"No matches found for pattern '{pattern}' in '{search_path}'"

            # Format output based on mode, virtualizing paths for agent
            if output_mode == "files_with_matches":
                result = f"Found matches in {len(results)} file(s):\n"
                for file_path in results:
                    virtual_path = sandbox.virtualize_path(file_path)
                    result += f"{virtual_path}\n"
            elif output_mode == "content":
                result = f"Matches for pattern '{pattern}':\n\n"
                for entry in results:
                    # Content entries may contain file paths - virtualize them
                    # Format is typically "filepath:line:content" or just content
                    if isinstance(entry, str) and ":" in entry:
                        parts = entry.split(":", 2)
                        if len(parts) >= 2:
                            virtual_path = sandbox.virtualize_path(parts[0])
                            entry = ":".join([virtual_path] + parts[1:])
                    result += f"{entry}\n"
            elif output_mode == "count":
                result = f"Match counts for pattern '{pattern}':\n"
                for file_path, count in results:
                    virtual_path = sandbox.virtualize_path(file_path)
                    result += f"{virtual_path}: {count}\n"
            else:
                result = str(results)

            logger.info(
                "Grep completed successfully",
                pattern=pattern,
                path=search_path,
                output_mode=output_mode,
                results_count=len(results),
            )

            return result.rstrip()

        except Exception as e:
            error_msg = f"Failed to grep content: {str(e)}"
            logger.error(
                error_msg,
                pattern=pattern,
                path=search_path,
                error=str(e),
                exc_info=True,
            )
            return f"ERROR: {error_msg}"

    return grep
