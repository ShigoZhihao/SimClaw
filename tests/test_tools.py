# ====================================================================
# test_tools.py — tools/ のテスト
# ====================================================================

import pytest
from pathlib import Path
from simclaw.config import load_config
from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.tools.file_read import FileReadTool
from simclaw.tools.file_write import FileWriteTool
from simclaw.tools.shell_execute import ShellExecuteTool
from simclaw.tools.star_macro_write import StarMacroWriteTool

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture
def config():
    return load_config(str(CONFIG_PATH))


# --- ToolResult のテスト ---

def test_tool_result_success():
    result = ToolResult(success=True, output="OK")
    assert result.success is True
    assert result.output == "OK"
    assert result.error == ""


def test_tool_result_failure():
    result = ToolResult(success=False, output="", error="エラー発生")
    assert result.success is False
    assert result.error == "エラー発生"


# --- make_tool_definition のテスト ---

def test_make_tool_definition_format():
    defn = make_tool_definition(
        name="test_tool",
        description="テストツール",
        parameters={"type": "object", "properties": {}, "required": []}
    )
    assert defn["type"] == "function"
    assert defn["function"]["name"] == "test_tool"
    assert defn["function"]["description"] == "テストツール"


# --- FileReadTool のテスト ---

def test_file_read_success(config):
    """許可フォルダ内のファイルを読めるか。"""
    # テスト用ファイルを workspace に作る
    test_file = Path("./workspace/test_read_tool.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("line1\nline2\nline3\n")

    tool = FileReadTool(config)
    result = tool.run(str(test_file))

    assert result.success is True
    assert "line1" in result.output
    assert "3 lines" in result.output

    test_file.unlink()


def test_file_read_outside_denied(config):
    """許可フォルダ外のファイルは拒否されるか。"""
    tool = FileReadTool(config)
    result = tool.run("/etc/passwd")
    assert result.success is False
    assert "拒否" in result.error or "アクセス" in result.error


def test_file_read_max_lines(config):
    """max_lines で行数制限が効くか。"""
    test_file = Path("./workspace/test_maxlines.txt")
    test_file.write_text("\n".join([f"line{i}" for i in range(100)]))

    tool = FileReadTool(config)
    result = tool.run(str(test_file), max_lines=10)

    assert result.success is True
    assert "省略" in result.output

    test_file.unlink()


def test_file_read_not_found(config):
    """存在しないファイルはエラーになるか。"""
    tool = FileReadTool(config)
    result = tool.run("./workspace/nonexistent_xyz.txt")
    assert result.success is False


# --- FileWriteTool のテスト ---

def test_file_write_success(config):
    """許可フォルダへの書込みが成功するか。"""
    tool = FileWriteTool(config)
    result = tool.run("./workspace/test_write.txt", "テスト内容")
    assert result.success is True

    # 書込まれた内容を確認
    written = Path("./workspace/test_write.txt").read_text()
    assert written == "テスト内容"
    Path("./workspace/test_write.txt").unlink()


def test_file_write_append(config):
    """append モードで追記できるか。"""
    tool = FileWriteTool(config)
    tool.run("./workspace/test_append.txt", "最初の行\n")
    tool.run("./workspace/test_append.txt", "2行目\n", mode="append")

    content = Path("./workspace/test_append.txt").read_text()
    assert "最初の行" in content
    assert "2行目" in content
    Path("./workspace/test_append.txt").unlink()


def test_file_write_outside_denied(config):
    """許可フォルダ外への書込みは拒否されるか。"""
    tool = FileWriteTool(config)
    result = tool.run("/tmp/evil.txt", "悪意のある内容")
    assert result.success is False


# --- ShellExecuteTool のテスト ---

def test_shell_allowlisted_command(config):
    """許可されたコマンドが実行できるか。"""
    tool = ShellExecuteTool(config)
    result = tool.run("ls .")
    assert result.success is True


def test_shell_denied_command(config):
    """許可されていないコマンドは拒否されるか。"""
    tool = ShellExecuteTool(config)
    result = tool.run("rm -rf /")
    assert result.success is False


def test_shell_pipe_denied(config):
    """パイプ（|）は拒否されるか。"""
    tool = ShellExecuteTool(config)
    result = tool.run("ls . | grep py")
    assert result.success is False


# --- StarMacroWriteTool のテスト ---

def test_star_macro_write_java(config):
    """Javaマクロが書けるか。"""
    tool = StarMacroWriteTool(config)
    result = tool.run("test_macro.java", "// テストマクロ\npublic class Test {}")
    assert result.success is True
    # 後片付け
    macro_file = Path("./macros/test_macro.java")
    if macro_file.exists():
        macro_file.unlink()


def test_star_macro_write_invalid_ext(config):
    """不正な拡張子は拒否されるか。"""
    tool = StarMacroWriteTool(config)
    result = tool.run("evil.sh", "rm -rf /")
    assert result.success is False
    assert "拡張子" in result.error


# --- ToolRegistry のテスト ---

def test_tool_registry_has_basic_tools(config):
    """ToolRegistry が基本ツールを持っているか。"""
    from simclaw.tools import ToolRegistry
    registry = ToolRegistry(config)
    tools = registry.list_tools()
    assert "file_read" in tools
    assert "file_write" in tools
    assert "star_execute" in tools
    assert "shell_execute" in tools


def test_tool_registry_unknown_tool(config):
    """存在しないツールを実行するとエラーになるか。"""
    from simclaw.tools import ToolRegistry
    registry = ToolRegistry(config)
    result = registry.execute("nonexistent_tool", path="./test")
    assert result.success is False
    assert "存在しません" in result.error


def test_tool_registry_get_definitions(config):
    """get_tool_definitions() がリストを返すか。"""
    from simclaw.tools import ToolRegistry
    registry = ToolRegistry(config)
    defs = registry.get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) > 0
    assert all("function" in d for d in defs)
