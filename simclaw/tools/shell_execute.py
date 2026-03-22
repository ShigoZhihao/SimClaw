# ====================================================================
# tools/shell_execute.py — ホワイトリスト方式のシェルコマンド実行
# ====================================================================

import subprocess
import fnmatch
from simclaw.tools.base import ToolResult, make_tool_definition


class ShellExecuteTool:
    def __init__(self, config):
        self.mode = config.safety.shell.mode
        self.allowlist = config.safety.shell.allowlist

    def get_definition(self):
        return make_tool_definition(
            name="shell_execute",
            description=f"Execute an allowlisted shell command. Allowed patterns: {', '.join(self.allowlist)}",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"]
            }
        )

    def run(self, command):
        if self.mode == "deny":
            return ToolResult(success=False, output="", error="シェル実行は無効です")

        if not self._is_allowed(command):
            return ToolResult(success=False, output="",
                              error=f"'{command}' は許可されていません。許可パターン: {self.allowlist}")

        # 危険パターンの二重チェック（パイプ、リダイレクト等を全面禁止）
        for danger in ["|", ";", "&&", "||", "`", "$(", ">", ">>", "<"]:
            if danger in command:
                return ToolResult(success=False, output="",
                                  error=f"'{danger}' は禁止されています")

        try:
            result = subprocess.run(
                command.split(), capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            # 出力が長すぎる場合は切り詰める
            if len(output) > 5000:
                output = output[:5000] + "\n... (5000文字で切り詰め)"
            return ToolResult(
                success=(result.returncode == 0), output=output,
                error=result.stderr if result.returncode != 0 else ""
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="タイムアウト（30秒）")

    def _is_allowed(self, command):
        """fnmatch でホワイトリストと照合する。"""
        return any(fnmatch.fnmatch(command, p) for p in self.allowlist)
