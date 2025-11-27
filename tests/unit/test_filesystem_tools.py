"""Tests for filesystem tools."""

import pytest
from unittest.mock import Mock, MagicMock
from src.agent.tools.filesystem import create_filesystem_tools


@pytest.fixture
def mock_sandbox():
    """Create a mock sandbox for testing."""
    sandbox = Mock()
    sandbox.config = Mock()
    sandbox.config.filesystem = Mock()
    sandbox.config.filesystem.enable_path_validation = True
    sandbox.config.filesystem.allowed_directories = ["/home/daytona", "/tmp"]
    # Add normalize_path mock that returns the path as-is
    sandbox.normalize_path = Mock(side_effect=lambda x: x)
    # Pre-create mock placeholders (tests will override with specific return values)
    # These are now sync methods called via asyncio.to_thread()
    sandbox.read_file = Mock()
    sandbox.read_file_range = Mock()
    sandbox.write_file = Mock()
    sandbox.edit_file = Mock()

    return sandbox


class TestReadFileTool:
    """Tests for read_file tool."""

    @pytest.mark.asyncio
    async def test_read_file_success(self, mock_sandbox):
        """Test successful file read."""
        mock_sandbox.validate_path = Mock(return_value=True)
        mock_sandbox.read_file = Mock(return_value="Hello, world!")

        read_file, _, _ = create_filesystem_tools(mock_sandbox)
        result = await read_file.ainvoke({"file_path": "test.txt"})

        # Result is in cat -n format with line numbers
        assert "Hello, world!" in result
        assert "ERROR" not in result

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, mock_sandbox):
        """Test reading non-existent file."""
        mock_sandbox.validate_path = Mock(return_value=True)
        mock_sandbox.read_file = Mock(return_value=None)

        read_file, _, _ = create_filesystem_tools(mock_sandbox)
        result = await read_file.ainvoke({"file_path": "missing.txt"})

        assert "ERROR" in result
        assert "File not found" in result

    @pytest.mark.asyncio
    async def test_read_file_access_denied(self, mock_sandbox):
        """Test reading file outside allowed directories."""
        mock_sandbox.validate_path = Mock(return_value=False)

        read_file, _, _ = create_filesystem_tools(mock_sandbox)
        result = await read_file.ainvoke({"file_path": "/etc/passwd"})

        assert "ERROR" in result
        assert "Access denied" in result


class TestWriteFileTool:
    """Tests for write_file tool."""

    @pytest.mark.asyncio
    async def test_write_file_success(self, mock_sandbox):
        """Test successful file write."""
        mock_sandbox.validate_path = Mock(return_value=True)
        mock_sandbox.write_file = Mock(return_value=True)
        mock_sandbox.virtualize_path = Mock(return_value="output.txt")

        _, write_file, _ = create_filesystem_tools(mock_sandbox)
        result = await write_file.ainvoke({
            "file_path": "output.txt",
            "content": "Test content"
        })

        # Result format: "Wrote X bytes to path"
        assert "Wrote 12 bytes" in result
        assert "ERROR" not in result

    @pytest.mark.asyncio
    async def test_write_file_failure(self, mock_sandbox):
        """Test failed file write."""
        mock_sandbox.validate_path = Mock(return_value=True)
        mock_sandbox.write_file = Mock(return_value=False)

        _, write_file, _ = create_filesystem_tools(mock_sandbox)
        result = await write_file.ainvoke({
            "file_path": "output.txt",
            "content": "Test"
        })

        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_write_file_access_denied(self, mock_sandbox):
        """Test writing file outside allowed directories."""
        mock_sandbox.validate_path = Mock(return_value=False)

        _, write_file, _ = create_filesystem_tools(mock_sandbox)
        result = await write_file.ainvoke({
            "file_path": "/etc/test.txt",
            "content": "Test"
        })

        assert "ERROR" in result
        assert "Access denied" in result


class TestEditFileTool:
    """Tests for edit_file tool."""

    @pytest.mark.asyncio
    async def test_edit_file_success(self, mock_sandbox):
        """Test successful file edit."""
        mock_sandbox.validate_path = Mock(return_value=True)
        mock_sandbox.edit_file = Mock(return_value={
            "success": True,
            "changed": True,
            "message": "Successfully edited test.txt"
        })

        _, _, edit_file = create_filesystem_tools(mock_sandbox)
        result = await edit_file.ainvoke({
            "file_path": "test.txt",
            "old_string": "old",
            "new_string": "new"
        })

        # Result returns the message from edit_file
        assert "Successfully edited" in result
        assert "ERROR" not in result

    @pytest.mark.asyncio
    async def test_edit_file_access_denied(self, mock_sandbox):
        """Test editing file outside allowed directories."""
        mock_sandbox.validate_path = Mock(return_value=False)

        _, _, edit_file = create_filesystem_tools(mock_sandbox)
        result = await edit_file.ainvoke({
            "file_path": "/etc/test.txt",
            "old_string": "old",
            "new_string": "new"
        })

        assert "ERROR" in result
        assert "Access denied" in result
