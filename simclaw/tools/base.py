# ====================================================================
# tools/base.py — 全ツール共通のフォーマット
# ====================================================================
#
# 【このファイルは何？】
# すべてのツールが使う「結果の箱（ToolResult）」と
# 「定義の作り方（make_tool_definition）」を定義する。
#
# 【なぜ必要？】
# LLMに「こういうツールが使えます」と伝えるには
# OpenAI Function Calling 形式の JSON が必要。
# 各ツールが個別に作ると書き方がバラバラになるため、
# このファイルで一元管理する。
#
# 【どう使う？】
# result = ToolResult(success=True, output="ファイルを読みました")
# definition = make_tool_definition("file_read", "ファイルを読む", {...})
# ====================================================================


class ToolResult:
    """ツールの実行結果を入れる箱。"""
    def __init__(self, success, output, error=""):
        self.success = success  # True=成功, False=失敗
        self.output = output    # 出力テキスト（LLMに渡す）
        self.error = error      # エラーメッセージ


def make_tool_definition(name, description, parameters):
    """ツール定義を「OpenAI Function Calling形式」に変換する。

    LLMに「こういうツールが使えますよ」と伝える標準的な書き方。

    引数:
        name: ツール名（例: "file_read"）
        description: 説明文（LLMがどのツールを使うか判断するのに使う）
        parameters: JSONSchema形式のパラメータ定義
    戻り値:
        OpenAI Function Calling 形式の辞書
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
    }
