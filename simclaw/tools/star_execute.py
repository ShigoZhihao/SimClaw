# ====================================================================
# tools/star_execute.py — STAR-CCM+ バッチ実行（人間承認必須）
# ====================================================================

import subprocess
from pathlib import Path
from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.safety import SafetyGuard


class StarExecuteTool:
    def __init__(self, config):
        self.config = config
        self.guard = SafetyGuard(config.safety)
        self.starccm = config.starccm
        self.workspaces_dir = Path(config.paths.workspaces_dir)

    def get_definition(self):
        return make_tool_definition(
            name="star_execute",
            description=(
                "Execute a STAR-CCM+ macro in batch mode. "
                "Requires human approval before execution."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "macro_path": {"type": "string", "description": "Path to .java or .py macro"},
                    "sim_file": {"type": "string", "description": "Optional .sim file path"}
                },
                "required": ["macro_path"]
            }
        )

    def run(self, macro_path, sim_file=""):
        # 拡張子チェック
        ext = Path(macro_path).suffix.lower()
        if ext not in self.starccm.allowed_extensions:
            return ToolResult(success=False, output="",
                              error=f"拡張子 '{ext}' は許可されていません")
        try:
            safe_macro = self.guard.validate_read_path(macro_path)
        except (PermissionError, FileNotFoundError) as e:
            return ToolResult(success=False, output="", error=str(e))

        # コマンド構築
        cmd = [self.starccm.executable] + self.starccm.default_args + [str(safe_macro)]
        if sim_file:
            try:
                safe_sim = self.guard.validate_read_path(sim_file)
                cmd.append(str(safe_sim))
            except (PermissionError, FileNotFoundError) as e:
                return ToolResult(success=False, output="", error=str(e))

        # コマンド安全性チェック
        try:
            self.guard.validate_starccm_command(cmd, self.starccm)
        except PermissionError as e:
            return ToolResult(success=False, output="", error=str(e))

        # 実行（人間承認は agent.py 側で行う）
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.starccm.timeout_seconds,
                cwd=str(self.workspaces_dir),
            )
            output = f"=== STAR-CCM+ Output ===\n{result.stdout}"
            if result.stderr:
                output += f"\n=== Errors ===\n{result.stderr}"
            return ToolResult(
                success=(result.returncode == 0), output=output,
                error=result.stderr if result.returncode != 0 else ""
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="",
                              error=f"タイムアウト（{self.starccm.timeout_seconds}秒）")
        except FileNotFoundError:
            return ToolResult(success=False, output="",
                              error=f"STAR-CCM+が見つかりません: {self.starccm.executable}")
