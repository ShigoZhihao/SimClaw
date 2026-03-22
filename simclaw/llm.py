# ====================================================================
# llm.py — ローカルLLMとの通信
# ====================================================================
#
# 【このファイルは何？】
# Ollama / LM Studio などのローカルLLMに接続して会話するクライアント。
# 外部クラウドAPIへの接続は絶対に行わない。
#
# 【なぜ openai ライブラリなのにOpenAIを使わない？】
# openai ライブラリは「通信のルール（OpenAI API仕様）」を実装したもの。
# そのルールに従うサーバーなら何でも使える。
# Ollama も LM Studio も同じルールに対応しているので、
# base_url を localhost に変えるだけで使える。
#
# 【どう使う？】
# client = LLMClient(config.llm)
# response = client.chat([{"role": "user", "content": "こんにちは"}])
# print(response.content)  → "こんにちは！何かお手伝いできますか？"
# ====================================================================

import json
import re
from urllib.parse import urlparse
from openai import OpenAI


class LLMResponse:
    """LLMからの返事を入れる箱。"""
    def __init__(self, content, tool_calls=None, usage=None):
        self.content = content          # テキスト応答
        self.tool_calls = tool_calls    # ツール呼び出し（あれば）
        self.usage = usage or {}        # トークン使用量


class LLMClient:
    """ローカルLLMと会話するクライアント。
    ★ 外部クラウドAPIには絶対に接続しない。"""

    def __init__(self, config):
        # --- localhost以外を禁止する安全チェック ---
        # urlparse でホスト名を取り出して確認する
        allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
        parsed = urlparse(config.base_url)
        if parsed.hostname not in allowed_hosts:
            raise ValueError(
                f"セキュリティエラー: '{parsed.hostname}' は許可されていません。\n"
                f"localhost / 127.0.0.1 のみ使用可能です。\n"
                f"設定値: {config.base_url}"
            )

        # api_key="not-needed": ローカルLLMにキーは不要だが
        # openaiライブラリが「キーがない」とエラーを出すのでダミーを渡す
        self.client = OpenAI(base_url=config.base_url, api_key="not-needed")
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    def chat(self, messages, tools=None):
        """ローカルLLMにメッセージを送り、返事をもらう。

        引数:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            tools: ツール定義リスト（なければ None）
        戻り値:
            LLMResponse
        エラー:
            ConnectionError: LLMに接続できない場合
        """
        # 送信パラメータを組み立てる
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        # ツールが指定されている場合は追加する
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        try:
            raw_response = self.client.chat.completions.create(**request_params)
        except Exception as e:
            raise ConnectionError(
                f"ローカルLLMに接続できません。\n"
                f"  接続先: {self.client.base_url}\n"
                f"  Ollamaが起動しているか確認: ollama serve\n"
                f"  エラー: {e}"
            )

        # レスポンスからメッセージを取り出す
        choice = raw_response.choices[0]
        message = choice.message

        # --- ツール呼び出しの抽出 ---
        tool_calls = None
        if message.tool_calls:
            # 標準の Function Calling 形式で返ってきた場合
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        # Function Calling非対応モデルのフォールバック
        # テキストに JSON が埋め込まれている場合を検出する
        if tool_calls is None and tools and message.content:
            tool_calls = self._parse_tool_calls_from_text(message.content)

        # トークン使用量を取り出す（ないモデルもあるので安全に処理）
        usage = {}
        if raw_response.usage:
            usage = {
                "prompt_tokens": raw_response.usage.prompt_tokens,
                "completion_tokens": raw_response.usage.completion_tokens,
            }

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            usage=usage,
        )

    def _parse_tool_calls_from_text(self, text):
        """Function Calling非対応モデル用フォールバック。
        テキストから {"tool": "...", "args": {...}} を探す。

        引数:
            text: LLMが返したテキスト全体
        戻り値:
            ツール呼び出しリスト、または None
        """
        # ネストしない JSON オブジェクトを正規表現で探す
        json_pattern = r'\{[^{}]*"tool"[^{}]*"args"[^{}]*\{[^{}]*\}[^{}]*\}'
        matches = re.findall(json_pattern, text)
        if not matches:
            return None

        tool_calls = []
        for match in matches:
            try:
                parsed = json.loads(match)
                # "tool" と "args" の両方があるものだけ有効とする
                if "tool" in parsed and "args" in parsed:
                    tool_calls.append({
                        "id": f"fallback_{len(tool_calls)}",
                        "name": parsed["tool"],
                        "arguments": parsed["args"],
                    })
            except json.JSONDecodeError:
                # JSON として解析できないものは無視する
                continue

        return tool_calls if tool_calls else None
