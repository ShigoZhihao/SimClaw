# ====================================================================
# tools/doc_search.py — ドキュメントRAG検索
# ====================================================================

from simclaw.tools.base import ToolResult, make_tool_definition


class DocSearchTool:
    def __init__(self, retriever):
        self.retriever = retriever

    def get_definition(self):
        return make_tool_definition(
            name="doc_search",
            description=(
                "Search STAR-CCM+ documentation (user guides, API references). "
                "Use BEFORE writing any macro code."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results (default: 5)"}
                },
                "required": ["query"]
            }
        )

    def run(self, query, top_k=5):
        results = self.retriever.search(query, top_k)
        if not results:
            return ToolResult(success=True, output="関連ドキュメントが見つかりませんでした。")
        lines = [
            f"[{i}] (source: {r['source']}, relevance: {r['score']:.2f})\n{r['text']}"
            for i, r in enumerate(results, 1)
        ]
        return ToolResult(success=True, output="\n\n".join(lines))
