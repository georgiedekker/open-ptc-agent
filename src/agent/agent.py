"""PTC Agent - Main agent using deepagent with Programmatic Tool Calling pattern.

This module creates a PTC agent that:
- Uses deepagent's create_deep_agent for orchestration
- Integrates Daytona sandbox via DaytonaBackend
- Provides MCP tools through execute_code
- Supports sub-agent delegation for specialized tasks
"""

from typing import Any, Dict, List, Optional

import structlog
from deepagents import create_deep_agent

from src.ptc_core.mcp_registry import MCPRegistry
from src.ptc_core.sandbox import PTCSandbox, ExecutionResult

from src.agent.backends import DaytonaBackend
from src.agent.config import AgentConfig
from src.agent.tools import (
    create_execute_bash_tool,
    create_execute_code_tool,
    create_filesystem_tools,
    create_glob_tool,
    create_grep_tool,
)
from src.utils.storage.storage_uploader import is_storage_enabled
from src.agent.prompts import get_loader, format_tool_summary, build_mcp_section
from src.agent.subagents import create_subagents_from_names

logger = structlog.get_logger(__name__)


# Default limits for sub-agent coordination
DEFAULT_MAX_CONCURRENT_TASK_UNITS = 3
DEFAULT_MAX_TASK_ITERATIONS = 3
DEFAULT_MAX_GENERAL_ITERATIONS = 10


class PTCAgent:
    """Agent that uses deepagent with Programmatic Tool Calling (PTC) pattern for MCP tool execution.

    This agent:
    - Uses deepagent's built-in filesystem tools via DaytonaBackend
    - Provides execute_code tool for MCP tool invocation
    - Supports sub-agent delegation for specialized tasks
    """

    def __init__(self, config: AgentConfig):
        """Initialize PTC agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.llm = config.get_llm_client()

        logger.info(
            "Initialized PTCAgent with deepagent",
            provider=config.llm_definition.provider,
            model=config.llm_definition.model_id,
        )

    def _build_system_prompt(self, tool_summary: str) -> str:
        """Build the system prompt for the agent.

        Args:
            tool_summary: Formatted MCP tool summary

        Returns:
            Complete system prompt
        """
        loader = get_loader()

        # Render the main system prompt with all variables
        return loader.get_system_prompt(
            tool_summary=tool_summary,
            max_concurrent_task_units=DEFAULT_MAX_CONCURRENT_TASK_UNITS,
            max_task_iterations=DEFAULT_MAX_TASK_ITERATIONS,
            storage_enabled=is_storage_enabled(),
            include_examples=True,
            include_anti_patterns=True,
            for_task_workflow=True,
        )

    def _get_tool_summary(self, mcp_registry: MCPRegistry) -> str:
        """Get formatted tool summary for prompts.

        Args:
            mcp_registry: MCP registry

        Returns:
            Formatted tool summary string
        """
        tools_by_server = mcp_registry.get_all_tools()

        # Convert to format expected by formatter
        tools_dict = {}
        for server_name, tools in tools_by_server.items():
            tools_dict[server_name] = [tool.to_dict() for tool in tools]

        # Build server configs dict for formatter (only enabled servers)
        server_configs = {s.name: s for s in self.config.mcp.servers if s.enabled}

        # Get tool exposure mode from config
        mode = self.config.mcp.tool_exposure_mode

        return format_tool_summary(tools_dict, mode=mode, server_configs=server_configs)

    def create_agent(
        self,
        sandbox: PTCSandbox,
        mcp_registry: MCPRegistry,
        subagent_names: List[str] = None,
        additional_subagents: List[Dict[str, Any]] = None,
    ) -> Any:
        """Create a deepagent with PTC pattern capabilities.

        Args:
            sandbox: PTCSandbox instance for code execution
            mcp_registry: MCPRegistry with available MCP tools
            subagent_names: List of subagent names to include (default: ["research"])
            additional_subagents: Additional sub-agent configurations

        Returns:
            Configured deepagent that can execute tasks
        """
        # Create the execute_code tool for MCP invocation
        execute_code_tool = create_execute_code_tool(sandbox, mcp_registry)

        # Create the Bash tool for shell command execution
        bash_tool = create_execute_bash_tool(sandbox)

        # Start with base tools
        tools = [execute_code_tool, bash_tool]

        # Always create backend for FilesystemMiddleware
        # (it handles ls, and provides fallback for other operations)
        backend = DaytonaBackend(sandbox)

        # Conditional tool loading based on config
        if self.config.use_custom_filesystem_tools:
            # Add custom filesystem tools with SAME NAMES as middleware tools
            # They will OVERRIDE middleware tools (same name + later position wins)
            read_file, write_file, edit_file = create_filesystem_tools(sandbox)
            tools.extend([
                read_file,                        # overrides middleware read_file
                write_file,                       # overrides middleware write_file
                edit_file,                        # overrides middleware edit_file
                create_glob_tool(sandbox),        # overrides middleware glob
                create_grep_tool(sandbox),        # overrides middleware grep
            ])
            logger.info(
                "Using custom filesystem tools (overriding middleware)",
                tools=["read_file", "write_file", "edit_file", "glob", "grep"],
            )
        else:
            logger.info(
                "Using deepagents native filesystem middleware",
                tools=["read_file", "write_file", "edit_file", "glob", "grep", "ls"],
            )

        # Get tool summary for system prompt
        tool_summary = self._get_tool_summary(mcp_registry)

        # Build system prompt
        system_prompt = self._build_system_prompt(tool_summary)

        # Default to research subagent if none specified
        if subagent_names is None:
            subagent_names = ["research"]

        # Create subagents from names using the registry
        subagents = create_subagents_from_names(
            names=subagent_names,
            sandbox=sandbox,
            mcp_registry=mcp_registry,
            max_researcher_iterations=DEFAULT_MAX_TASK_ITERATIONS,
            max_iterations=DEFAULT_MAX_GENERAL_ITERATIONS,
        )

        if additional_subagents:
            subagents.extend(additional_subagents)

        logger.info(
            "Creating deepagent",
            tool_count=len(tools),
            subagent_count=len(subagents),
            use_custom_filesystem_tools=self.config.use_custom_filesystem_tools,
        )

        # Create deepagent with backend
        # Note: deep-agent automatically adds these middlewares:
        # - TodoListMiddleware, SummarizationMiddleware, FilesystemMiddleware,
        # - SubAgentMiddleware, AnthropicPromptCachingMiddleware, PatchToolCallsMiddleware
        agent = create_deep_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
            subagents=subagents if subagents else None,
            backend=backend,
        )

        return agent


class PTCExecutor:
    """Executor that combines agent and sandbox for complete task execution."""

    def __init__(self, agent: PTCAgent, mcp_registry: MCPRegistry):
        """Initialize executor.

        Args:
            agent: PTC agent for task execution
            mcp_registry: MCP registry with available tools
        """
        self.agent = agent
        self.mcp_registry = mcp_registry

        logger.info("Initialized PTCExecutor")

    async def execute_task(
        self,
        task: str,
        sandbox: PTCSandbox,
        max_retries: int = 3,
    ) -> ExecutionResult:
        """Execute a task using deepagent with automatic error recovery.

        Args:
            task: User's task description
            sandbox: PTCSandbox instance
            max_retries: Maximum retry attempts

        Returns:
            Final execution result
        """
        logger.info("Executing task with deepagent", task=task[:100])

        # Create the agent with injected dependencies
        agent = self.agent.create_agent(sandbox, self.mcp_registry)

        try:
            # Configure recursion limit
            recursion_limit = max(max_retries * 5, 15)

            # Execute task via deepagent
            agent_result = await agent.ainvoke(
                {"messages": [("user", task)]},
                config={"recursion_limit": recursion_limit},
            )

            # Parse result into ExecutionResult
            return await self._parse_agent_result(agent_result, sandbox)

        except Exception as e:
            logger.error("Agent execution failed", error=str(e))

            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Agent execution error: {str(e)}",
                duration=0,
                files_created=[],
                files_modified=[],
                execution_id="agent_error",
                code_hash="",
            )

    async def _parse_agent_result(
        self, agent_result: dict, sandbox: PTCSandbox
    ) -> ExecutionResult:
        """Parse deepagent result into ExecutionResult.

        Args:
            agent_result: Result from agent.ainvoke()
            sandbox: Sandbox instance to query for files

        Returns:
            ExecutionResult with execution details
        """
        messages = agent_result.get("messages", [])

        if not messages:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Agent returned no messages",
                duration=0,
                files_created=[],
                files_modified=[],
                execution_id="no_messages",
                code_hash="",
            )

        # Find tool messages
        tool_messages = [
            msg for msg in messages if hasattr(msg, "type") and msg.type == "tool"
        ]

        if not tool_messages:
            # Extract final AI message
            ai_messages = [
                msg for msg in messages if hasattr(msg, "type") and msg.type == "ai"
            ]
            final_message = ai_messages[-1].content if ai_messages else "No execution"

            return ExecutionResult(
                success=True,  # Agent completed without code execution
                stdout=final_message,
                stderr="",
                duration=0,
                files_created=[],
                files_modified=[],
                execution_id="no_tool_calls",
                code_hash="",
            )

        # Get last tool message
        last_tool_msg = tool_messages[-1]
        observation = (
            last_tool_msg.content
            if hasattr(last_tool_msg, "content")
            else str(last_tool_msg)
        )

        # Check success
        success = "SUCCESS" in observation or "ERROR" not in observation

        # Extract stdout/stderr
        if success:
            stdout = observation.replace("SUCCESS", "").strip()
            stderr = ""
        else:
            stdout = ""
            stderr = observation.replace("ERROR", "").strip()

        # Get files from sandbox
        files_created = []
        try:
            if hasattr(sandbox, "_list_result_files"):
                result_files = await sandbox._list_result_files()
                files_created = [f for f in result_files if f]
        except Exception:
            pass

        return ExecutionResult(
            success=success,
            stdout=stdout,
            stderr=stderr,
            duration=0.0,
            files_created=files_created,
            files_modified=[],
            execution_id=f"agent_step_{len(tool_messages)}",
            code_hash="",
        )


# For LangGraph deployment compatibility
async def create_ptc_agent(config: Optional[AgentConfig] = None) -> PTCAgent:
    """Create a PTCAgent instance.

    Factory function for LangGraph deployment.

    Args:
        config: Optional agent configuration. If None, loads from default.

    Returns:
        Configured PTCAgent
    """
    if config is None:
        config = await AgentConfig.load()
        config.validate_api_keys()

    return PTCAgent(config)


# Legacy aliases for backward compatibility
CodeActAgent = PTCAgent
CodeExecutor = PTCExecutor
create_codeact_agent = create_ptc_agent
