# ====================================================================
# memory/conversation.py — 短期記憶（会話履歴）
# ====================================================================
#
# 【このファイルは何？】
# LLMに渡す「messages」リストを管理する。
# ロールは "system"（指示）、"user"（人間の入力）、
# "assistant"（LLMの応答）、"tool"（ツール結果）の4種類。
#
# 【なぜ必要？】
# メッセージが増えすぎるとコンテキストウィンドウを溢れる。
# max_messages を超えたら古いものから削除する（systemは保持）。
#
# 【どう使う？】
# mem = ConversationMemory(max_messages=40)
# mem.add("user", "メッシュを設定して")
# mem.add("assistant", "わかりました")
# messages = mem.get_messages()  → LLMに渡せる形式で返す
# ====================================================================


class ConversationMemory:
    """会話履歴を管理する短期記憶。"""

    def __init__(self, max_messages=40):
        self.messages = []
        self.max_messages = max_messages  # system 以外の最大保持数

    def add(self, role, content, tool_call_id="", name=""):
        """メッセージを追加する。

        引数:
            role: "system" | "user" | "assistant" | "tool"
            content: メッセージ内容
            tool_call_id: ツール結果の場合に必要な ID
            name: ツール名（ツール結果の場合）
        """
        message = {"role": role, "content": content}
        # ツール結果の場合は追加フィールドが必要
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        if name:
            message["name"] = name
        self.messages.append(message)
        self._trim()

    def add_tool_calls(self, content, tool_calls_raw):
        """LLMがツールを呼び出した応答を記録する。
        Function Calling 形式で保存することで、次のターンで
        LLMがツール結果を受け取れる。

        引数:
            content: LLMのテキスト応答（空の場合もある）
            tool_calls_raw: ツール呼び出しリスト（agent.py が生成）
        """
        message = {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        # arguments は文字列で渡す必要がある
                        "arguments": str(tc["arguments"])
                    }
                }
                for tc in tool_calls_raw
            ]
        }
        self.messages.append(message)
        # tool_calls を含むメッセージは trim せずそのまま（対応するtoolメッセージが必要なため）

    def get_messages(self):
        """LLMに渡せる形式でメッセージリストを返す。"""
        return list(self.messages)

    def clear_non_system(self):
        """system メッセージ以外をすべてクリアする。"""
        self.messages = [m for m in self.messages if m["role"] == "system"]

    def _trim(self):
        """max_messages を超えた場合、古い非systemメッセージを削除する。"""
        # system メッセージは常に保持する
        system_msgs = [m for m in self.messages if m["role"] == "system"]
        other_msgs = [m for m in self.messages if m["role"] != "system"]

        # 上限を超えた分だけ古いものから削除する
        if len(other_msgs) > self.max_messages:
            other_msgs = other_msgs[-self.max_messages:]

        self.messages = system_msgs + other_msgs
