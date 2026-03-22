# ====================================================================
# tools/memory_tool.py — メモリ検索と書込み
# ====================================================================

from simclaw.tools.base import ToolResult, make_tool_definition


class MemorySearchTool:
    """過去の記憶をハイブリッド検索するツール。"""

    def __init__(self, hybrid_search, workspace_manager):
        self.search_engine = hybrid_search
        self.ws = workspace_manager

    def get_definition(self):
        return make_tool_definition(
            name="memory_search",
            description="Search past memories and learnings (errors, solutions, patterns).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"}
                },
                "required": ["query"]
            }
        )

    def run(self, query):
        results = self.search_engine.search(query, "memory", top_k=5)
        if not results:
            return ToolResult(success=True, output="該当する記憶なし。")
        lines = [f"[{i}] (relevance: {r['score']:.2f})\n{r['text']}"
                 for i, r in enumerate(results, 1)]
        return ToolResult(success=True, output="\n\n".join(lines))


class MemoryWriteTool:
    """MEMORY.md に新しい知識を書き込むツール。"""

    def __init__(self, persistent_memory):
        self.persistent = persistent_memory

    def get_definition(self):
        return make_tool_definition(
            name="memory_write",
            description="Save a learning to MEMORY.md. Categories: 成功パターン, 失敗パターンと解決策, 学んだこと",
            parameters={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category name"},
                    "content": {"type": "string", "description": "What you learned"}
                },
                "required": ["category", "content"]
            }
        )

    def run(self, category, content):
        self.persistent.save_learning(category, content)
        return ToolResult(success=True, output=f"MEMORY.mdに記録: [{category}] {content[:100]}")
