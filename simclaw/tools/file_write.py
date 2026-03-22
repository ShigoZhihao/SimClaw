# ====================================================================
# tools/file_write.py — 制限付きファイル書込み
# ====================================================================

from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.safety import SafetyGuard


class FileWriteTool:
    def __init__(self, config):
        self.guard = SafetyGuard(config.safety)

    def get_definition(self):
        return make_tool_definition(
            name="file_write",
            description="Write content to a file within allowed directories.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                    "mode": {"type": "string", "description": "'overwrite' or 'append' (default: overwrite)"}
                },
                "required": ["path", "content"]
            }
        )

    def run(self, path, content, mode="overwrite"):
        try:
            safe_path = self.guard.validate_write_path(path)
            # 親ディレクトリが存在しない場合は作成する
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            open_mode = "a" if mode == "append" else "w"
            with open(safe_path, open_mode, encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"ファイル書込み完了: {path}")
        except PermissionError as e:
            return ToolResult(success=False, output="", error=str(e))
