# ====================================================================
# tools/web_search.py — DuckDuckGo Web検索（APIキー不要）
# ====================================================================

import httpx
from simclaw.tools.base import ToolResult, make_tool_definition


class WebSearchTool:
    def __init__(self, config):
        pass  # 特に設定不要

    def get_definition(self):
        return make_tool_definition(
            name="web_search",
            description="Search the web via DuckDuckGo. No API key needed.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Results count (default: 5)"}
                },
                "required": ["query"]
            }
        )

    def run(self, query, max_results=5):
        try:
            response = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                timeout=10,
            )
            data = response.json()
            results = []
            if data.get("Abstract"):
                results.append(f"[概要] {data['Abstract']}\n  出典: {data.get('AbstractURL','')}")
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(f"[関連] {topic['Text']}\n  URL: {topic.get('FirstURL','')}")
            if not results:
                return ToolResult(success=True, output=f"'{query}' の結果なし。別のキーワードで試してください。")
            return ToolResult(success=True, output="\n\n".join(results))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Web検索エラー: {e}")
