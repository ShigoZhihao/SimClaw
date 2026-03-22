# ====================================================================
# test_config.py — config.py のテスト
# ====================================================================

import pytest
from pathlib import Path
from simclaw.config import load_config, AppConfig


# テスト用の設定ファイルパス
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def test_load_config_returns_appconfig():
    """load_config() が AppConfig を返すか確認。"""
    config = load_config(str(CONFIG_PATH))
    assert isinstance(config, AppConfig)


def test_llm_config():
    """LLM設定が正しく読み込まれるか確認。"""
    config = load_config(str(CONFIG_PATH))
    assert config.llm.base_url == "http://localhost:11434/v1"
    assert config.llm.model == "qwen3.5:14b"
    assert config.llm.temperature == 0.2
    assert config.llm.max_tokens == 4096


def test_safety_config():
    """セキュリティ設定が正しく読み込まれるか確認。"""
    config = load_config(str(CONFIG_PATH))
    assert len(config.safety.allowed_read_dirs) > 0
    assert len(config.safety.allowed_write_dirs) > 0
    assert config.safety.shell.mode == "allowlist"
    assert "star_execute" in config.safety.require_human_approval


def test_starccm_config():
    """STAR-CCM+設定が正しく読み込まれるか確認。"""
    config = load_config(str(CONFIG_PATH))
    assert ".java" in config.starccm.allowed_extensions
    assert ".py" in config.starccm.allowed_extensions
    assert config.starccm.timeout_seconds == 3600


def test_memory_config_hybrid_search():
    """ハイブリッド検索の重みが正しく読み込まれるか確認。"""
    config = load_config(str(CONFIG_PATH))
    assert config.memory.vector_weight == 0.6
    assert config.memory.bm25_weight == 0.4


def test_file_not_found():
    """存在しないファイルを指定した場合にエラーが発生するか確認。"""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")
