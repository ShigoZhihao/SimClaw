# ====================================================================
# tools/log_read.py — ログ読取り・エラー抽出
# ====================================================================

from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.safety import SafetyGuard


class LogReadTool:
    def __init__(self, config):
        self.guard = SafetyGuard(config.safety)

    def get_definition(self):
        return make_tool_definition(
            name="log_read",
            description="Read STAR-CCM+ log files. Extracts errors, warnings, and tail.",
            parameters={
                "type": "object",
                "properties": {
                    "log_path": {"type": "string", "description": "Path to log file"},
                    "tail_lines": {"type": "integer", "description": "Lines from end (default: 100)"},
                    "filter_errors": {"type": "boolean", "description": "Extract ERROR/WARNING lines (default: true)"}
                },
                "required": ["log_path"]
            }
        )

    def run(self, log_path, tail_lines=100, filter_errors=True):
        try:
            safe_path = self.guard.validate_read_path(log_path)
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            output_parts = []
            total = len(all_lines)

            # ERROR/WARNING 行を抽出する
            if filter_errors:
                error_keywords = ["ERROR", "WARNING", "Exception", "FATAL", "SEVERE"]
                error_lines = [
                    f"L{i+1}: {line.rstrip()}"
                    for i, line in enumerate(all_lines)
                    if any(kw in line for kw in error_keywords)
                ]
                if error_lines:
                    output_parts.append(
                        f"=== Errors & Warnings ({len(error_lines)} lines) ===\n"
                        + "\n".join(error_lines[:50])
                    )

            # 末尾N行を追加する
            tail = all_lines[-tail_lines:] if tail_lines > 0 else all_lines
            output_parts.append(
                f"=== Last {min(tail_lines, total)} of {total} lines ===\n"
                + "".join(tail)
            )

            return ToolResult(success=True, output="\n\n".join(output_parts))
        except (PermissionError, FileNotFoundError) as e:
            return ToolResult(success=False, output="", error=str(e))
