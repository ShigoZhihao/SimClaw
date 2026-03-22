# ====================================================================
# tools/__init__.py — 全ツールをまとめて管理する
# ====================================================================
#
# 【このファイルは何？】
# ToolRegistry が「使えるツールの一覧」を持ち、
# エージェントが「このツールを使って」と言ったときに実行する。
#
# 【なぜ必要？】
# agent.py が個々のツールクラスを直接知る必要をなくす。
# ToolRegistry.execute("file_read", path="...") と呼ぶだけでOK。
# ====================================================================

from simclaw.tools.base import ToolResult
from simclaw.tools.file_read import FileReadTool
from simclaw.tools.file_write import FileWriteTool
from simclaw.tools.star_macro_write import StarMacroWriteTool
from simclaw.tools.star_execute import StarExecuteTool
from simclaw.tools.log_read import LogReadTool
from simclaw.tools.shell_execute import ShellExecuteTool
from simclaw.tools.web_search import WebSearchTool
from simclaw.tools.memory_tool import MemorySearchTool, MemoryWriteTool


class ToolRegistry:
    """使えるツールをまとめて管理する。"""

    def __init__(self, config, retriever=None,
                 hybrid_search=None, workspace_manager=None,
                 persistent_memory=None):
        self._tools = {}

        # 基本ツール（常に有効）
        self._tools["file_read"] = FileReadTool(config)
        self._tools["file_write"] = FileWriteTool(config)
        self._tools["log_read"] = LogReadTool(config)
        self._tools["star_macro_write"] = StarMacroWriteTool(config)
        self._tools["star_execute"] = StarExecuteTool(config)
        self._tools["shell_execute"] = ShellExecuteTool(config)
        self._tools["web_search"] = WebSearchTool(config)

        # ブラウザ（設定で有効な場合のみ）
        if config.safety.browser.enabled:
            from simclaw.tools.browser import BrowserTool
            self._tools["browser_fetch"] = BrowserTool(config)

        # RAG（retriever が渡された場合のみ）
        if retriever:
            from simclaw.tools.doc_search import DocSearchTool
            self._tools["doc_search"] = DocSearchTool(retriever)

        # メモリ（hybrid_search と workspace_manager が渡された場合のみ）
        if hybrid_search and workspace_manager:
            self._tools["memory_search"] = MemorySearchTool(hybrid_search, workspace_manager)
        if persistent_memory:
            self._tools["memory_write"] = MemoryWriteTool(persistent_memory)

    def get_tool_definitions(self):
        """全ツールの定義リストを返す（LLMに渡すため）。"""
        return [tool.get_definition() for tool in self._tools.values()]

    def execute(self, tool_name, **kwargs):
        """指定したツールを実行する。

        引数:
            tool_name: ツール名（例: "file_read"）
            **kwargs: ツールのパラメータ
        戻り値:
            ToolResult
        """
        if tool_name not in self._tools:
            return ToolResult(
                success=False, output="",
                error=(
                    f"ツール '{tool_name}' は存在しません。"
                    f"利用可能: {list(self._tools.keys())}"
                )
            )
        return self._tools[tool_name].run(**kwargs)

    def list_tools(self):
        """利用可能なツール名の一覧を返す。"""
        return list(self._tools.keys())
