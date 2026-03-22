# ====================================================================
# tools/browser.py — ブラウザ自動操作（ドメイン制限付き）
# ====================================================================

from urllib.parse import urlparse
from simclaw.tools.base import ToolResult, make_tool_definition


class BrowserTool:
    def __init__(self, config):
        self.enabled = config.safety.browser.enabled
        self.headless = config.safety.browser.headless
        self.allowed_domains = config.safety.browser.allowed_domains

    def get_definition(self):
        return make_tool_definition(
            name="browser_fetch",
            description=f"Fetch a web page. Allowed domains: {', '.join(self.allowed_domains)}",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "extract_selector": {"type": "string", "description": "Optional CSS selector"}
                },
                "required": ["url"]
            }
        )

    def run(self, url, extract_selector=""):
        if not self.enabled:
            return ToolResult(success=False, output="", error="ブラウザは無効です")

        # ドメイン制限チェック
        domain = urlparse(url).hostname or ""
        if not any(domain == d or domain.endswith("." + d) for d in self.allowed_domains):
            return ToolResult(success=False, output="",
                              error=f"ドメイン '{domain}' は許可されていません。許可: {self.allowed_domains}")

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                if extract_selector:
                    el = page.query_selector(extract_selector)
                    text = el.inner_text() if el else "(セレクタに一致なし)"
                else:
                    text = page.inner_text("body")
                browser.close()
            if len(text) > 8000:
                text = text[:8000] + "\n... (8000文字で切り詰め)"
            return ToolResult(success=True, output=text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"ブラウザエラー: {e}")
