# ====================================================================
# tools/star_macro_write.py — STAR-CCM+マクロ書出し
# ====================================================================

from pathlib import Path
from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.safety import SafetyGuard


class StarMacroWriteTool:
    def __init__(self, config):
        self.guard = SafetyGuard(config.safety)
        self.macros_dir = Path(config.paths.macros_dir)
        self.allowed_ext = config.starccm.allowed_extensions

    def get_definition(self):
        return make_tool_definition(
            name="star_macro_write",
            description=(
                "Write a STAR-CCM+ Java or Python macro file. "
                "Returns the saved path for use with star_execute."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "e.g. 'setup_mesh.java'"},
                    "content": {"type": "string", "description": "Complete macro source code"}
                },
                "required": ["filename", "content"]
            }
        )

    def run(self, filename, content):
        # 拡張子チェック（.java または .py のみ許可）
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_ext:
            return ToolResult(
                success=False, output="",
                error=f"拡張子 '{ext}' は許可されていません。許可: {self.allowed_ext}"
            )

        file_path = self.macros_dir / filename
        try:
            safe_path = self.guard.validate_write_path(str(file_path))
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"マクロ保存完了: {file_path}")
        except PermissionError as e:
            return ToolResult(success=False, output="", error=str(e))
