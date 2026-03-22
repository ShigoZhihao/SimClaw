# ====================================================================
# tools/file_read.py — 制限付きファイル読取り
# ====================================================================
#
# 【このファイルは何？】
# SafetyGuard を通して許可フォルダ内のファイルだけを読む。
# 行数制限あり（デフォルト200行）。バイナリファイルは拒否。
#
# 【どう使う？】
# tool = FileReadTool(config)
# result = tool.run(path="./workspace/MEMORY.md", max_lines=100)
# print(result.output)  → ファイルの中身
# ====================================================================

from simclaw.tools.base import ToolResult, make_tool_definition
from simclaw.safety import SafetyGuard


class FileReadTool:
    """制限付きファイル読取りツール。"""

    def __init__(self, config):
        # SafetyGuard でファイルアクセスを制限する
        self.guard = SafetyGuard(config.safety)

    def get_definition(self):
        """LLMに渡すツール定義を返す。"""
        return make_tool_definition(
            name="file_read",
            description="Read a file within allowed directories.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Max lines to read (default: 200, 0=all)"
                    }
                },
                "required": ["path"]
            }
        )

    def run(self, path, max_lines=200):
        """ファイルを読んで内容を返す。

        引数:
            path: 読み取るファイルのパス
            max_lines: 最大行数（0 なら全行）
        戻り値:
            ToolResult
        """
        try:
            # SafetyGuard でパスを検証（許可フォルダ外は PermissionError）
            safe_path = self.guard.validate_read_path(path)

            # ファイルを全行読み込む
            with open(safe_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total = len(lines)

            # 行数制限を適用する
            if max_lines > 0 and total > max_lines:
                lines = lines[:max_lines]
                content = "".join(lines) + f"\n\n... （残り {total - max_lines} 行省略）"
            else:
                content = "".join(lines)

            return ToolResult(
                success=True,
                output=f"=== {path} ({total} lines) ===\n{content}"
            )

        except PermissionError as e:
            return ToolResult(success=False, output="", error=str(e))
        except FileNotFoundError as e:
            return ToolResult(success=False, output="", error=str(e))
        except UnicodeDecodeError:
            return ToolResult(
                success=False, output="",
                error=f"{path} はバイナリファイルです。テキストファイルのみ読めます。"
            )
