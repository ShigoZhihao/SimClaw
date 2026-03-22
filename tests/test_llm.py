# ====================================================================
# test_llm.py — llm.py のテスト（モックを使用）
# ====================================================================
# 実際の Ollama は不要。モックで LLM の応答を模倣する。

import pytest
from unittest.mock import MagicMock, patch
from simclaw.llm import LLMClient, LLMResponse


class FakeLLMConfig:
    """テスト用のダミー LLM 設定。"""
    base_url = "http://localhost:11434/v1"
    model = "test-model"
    temperature = 0.2
    max_tokens = 1024


class FakeExternalConfig:
    """テスト用: 外部URLの設定（拒否されるべき）。"""
    base_url = "https://api.openai.com/v1"
    model = "gpt-4"
    temperature = 0.2
    max_tokens = 1024


def make_mock_response(content="テスト応答", tool_calls=None):
    """モックのLLMレスポンスを作る。"""
    mock_message = MagicMock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    return mock_response


# --- セキュリティチェックのテスト ---

def test_localhost_only_allowed():
    """localhost への接続は許可されるか。"""
    with patch("simclaw.llm.OpenAI"):
        client = LLMClient(FakeLLMConfig())
        assert client.model == "test-model"


def test_external_url_rejected():
    """外部URL（api.openai.com）は拒否されるか。"""
    with pytest.raises(ValueError, match="セキュリティエラー"):
        LLMClient(FakeExternalConfig())


def test_127_0_0_1_allowed():
    """127.0.0.1 への接続は許可されるか。"""
    class Config127:
        base_url = "http://127.0.0.1:11434/v1"
        model = "test"
        temperature = 0.2
        max_tokens = 1024

    with patch("simclaw.llm.OpenAI"):
        client = LLMClient(Config127())
        assert client is not None


# --- chat() のテスト ---

def test_chat_returns_llm_response():
    """chat() が LLMResponse を返すか。"""
    with patch("simclaw.llm.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.return_value = make_mock_response("こんにちは")

        client = LLMClient(FakeLLMConfig())
        response = client.chat([{"role": "user", "content": "テスト"}])

        assert isinstance(response, LLMResponse)
        assert response.content == "こんにちは"
        assert response.tool_calls is None


def test_chat_usage_captured():
    """chat() がトークン使用量を取得するか。"""
    with patch("simclaw.llm.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.return_value = make_mock_response()

        client = LLMClient(FakeLLMConfig())
        response = client.chat([{"role": "user", "content": "テスト"}])

        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20


def test_chat_connection_error():
    """LLMに接続できない場合 ConnectionError が発生するか。"""
    with patch("simclaw.llm.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.side_effect = Exception("接続失敗")

        client = LLMClient(FakeLLMConfig())
        with pytest.raises(ConnectionError, match="ローカルLLMに接続できません"):
            client.chat([{"role": "user", "content": "テスト"}])


# --- フォールバックパーサーのテスト ---

def test_parse_tool_calls_from_text():
    """テキスト内の JSON からツール呼び出しを抽出できるか。"""
    with patch("simclaw.llm.OpenAI"):
        client = LLMClient(FakeLLMConfig())

    text = 'ファイルを読みます。{"tool": "file_read", "args": {"path": "./workspace/MEMORY.md"}}'
    result = client._parse_tool_calls_from_text(text)

    assert result is not None
    assert len(result) == 1
    assert result[0]["name"] == "file_read"
    assert result[0]["arguments"]["path"] == "./workspace/MEMORY.md"


def test_parse_tool_calls_no_match():
    """ツール呼び出しが含まれないテキストは None を返すか。"""
    with patch("simclaw.llm.OpenAI"):
        client = LLMClient(FakeLLMConfig())

    result = client._parse_tool_calls_from_text("普通のテキスト応答です。")
    assert result is None
