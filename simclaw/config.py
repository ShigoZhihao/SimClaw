# ====================================================================
# config.py — 設定ファイル（config.yaml）を読み込む
# ====================================================================
#
# 【このファイルは何？】
# config.yaml の設定を Python のオブジェクトに変換する。
#
# 【なぜ必要？】
# yaml.safe_load() は辞書を返すだけ。
# config["llm"]["model"] より config.llm.model の方が
# タイポに気づきやすく、IDEの補完も効く。
#
# 【どう使う？】
# config = load_config("config.yaml")
# print(config.llm.model)  → "qwen3.5:14b"
# ====================================================================

import yaml
from pathlib import Path


class LLMConfig:
    """ローカルLLMの接続設定を入れる箱。"""
    def __init__(self, base_url, model, temperature=0.2,
                 max_tokens=4096, context_window=32000):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context_window = context_window


class EmbeddingConfig:
    """Embedding（文章→数値ベクトル変換）の設定。"""
    def __init__(self, model_name="intfloat/multilingual-e5-small", device="cpu"):
        self.model_name = model_name
        self.device = device


class RAGConfig:
    """RAG（ドキュメント検索）の設定。"""
    def __init__(self, docs_dir="./docs", collection_name="starccm_docs",
                 db_dir="./data/chromadb", chunk_size=512,
                 chunk_overlap=64, top_k=5):
        self.docs_dir = docs_dir
        self.collection_name = collection_name
        self.db_dir = db_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k


class WorkspaceConfig:
    """ワークスペースの設定。"""
    def __init__(self, dir="./workspace"):
        self.dir = dir


class SkillsConfig:
    """スキルディレクトリの設定。"""
    def __init__(self, dirs=None):
        self.dirs = dirs or ["./skills"]


class PathsConfig:
    """各種ディレクトリのパス設定。"""
    def __init__(self, workspaces_dir="./workspaces",
                 macros_dir="./macros", logs_dir="./logs"):
        self.workspaces_dir = workspaces_dir
        self.macros_dir = macros_dir
        self.logs_dir = logs_dir


class StarCCMConfig:
    """STAR-CCM+ 実行設定。"""
    def __init__(self, executable="", default_args=None,
                 allowed_extensions=None, timeout_seconds=3600):
        self.executable = executable
        self.default_args = default_args or ["-batch", "-np", "4"]
        self.allowed_extensions = allowed_extensions or [".java", ".py"]
        self.timeout_seconds = timeout_seconds


class MemoryConfig:
    """メモリ・会話履歴の設定。"""
    def __init__(self, daily_log_dir="./workspace/memory",
                 max_conversation_messages=40, auto_save_interval=5,
                 hybrid_search=None):
        self.daily_log_dir = daily_log_dir
        self.max_conversation_messages = max_conversation_messages
        self.auto_save_interval = auto_save_interval
        # hybrid_search は辞書なので個別に取り出す
        hs = hybrid_search or {}
        self.vector_weight = hs.get("vector_weight", 0.6)
        self.bm25_weight = hs.get("bm25_weight", 0.4)


class ContextConfig:
    """コンテキストウィンドウ管理の設定。"""
    def __init__(self, max_tokens=24000, compress_threshold=20000,
                 system_reserve=4000):
        self.max_tokens = max_tokens
        self.compress_threshold = compress_threshold
        self.system_reserve = system_reserve


class HeartbeatConfig:
    """定期チェックの設定。"""
    def __init__(self, enabled=False, interval_minutes=30):
        self.enabled = enabled
        self.interval_minutes = interval_minutes


class ShellConfig:
    """シェル実行の制限設定。"""
    def __init__(self, mode="allowlist", allowlist=None):
        self.mode = mode
        self.allowlist = allowlist or []


class BrowserConfig:
    """ブラウザ自動操作の制限設定。"""
    def __init__(self, enabled=True, headless=True, allowed_domains=None):
        self.enabled = enabled
        self.headless = headless
        self.allowed_domains = allowed_domains or []


class SafetyConfig:
    """セキュリティ全般の設定。"""
    def __init__(self, allowed_read_dirs=None, allowed_write_dirs=None,
                 shell=None, browser=None,
                 max_consecutive_errors=5, require_human_approval=None):
        self.allowed_read_dirs = allowed_read_dirs or []
        self.allowed_write_dirs = allowed_write_dirs or []
        # shell と browser はネストした辞書なので個別クラスに変換
        self.shell = ShellConfig(**(shell or {}))
        self.browser = BrowserConfig(**(browser or {}))
        self.max_consecutive_errors = max_consecutive_errors
        self.require_human_approval = require_human_approval or ["star_execute"]


class AppConfig:
    """全設定をまとめる箱。"""
    def __init__(self, llm, embedding, rag, workspace, skills,
                 paths, starccm, memory, context, heartbeat, safety):
        self.llm = llm
        self.embedding = embedding
        self.rag = rag
        self.workspace = workspace
        self.skills = skills
        self.paths = paths
        self.starccm = starccm
        self.memory = memory
        self.context = context
        self.heartbeat = heartbeat
        self.safety = safety


def load_config(path="config.yaml"):
    """config.yamlを読み込んでAppConfigを返す。

    引数:
        path: config.yaml のパス（デフォルト: "config.yaml"）
    戻り値:
        AppConfig オブジェクト
    エラー:
        FileNotFoundError: ファイルが存在しない場合
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")

    # yamlファイルを読み込んで辞書に変換
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # ** は辞書を展開する記法。
    # {"base_url": "...", "model": "..."} → LLMConfig(base_url="...", model="...")
    return AppConfig(
        llm=LLMConfig(**raw.get("llm", {})),
        embedding=EmbeddingConfig(**raw.get("embedding", {})),
        rag=RAGConfig(**raw.get("rag", {})),
        workspace=WorkspaceConfig(**raw.get("workspace", {})),
        skills=SkillsConfig(**raw.get("skills", {})),
        paths=PathsConfig(**raw.get("paths", {})),
        starccm=StarCCMConfig(**raw.get("starccm", {})),
        memory=MemoryConfig(**raw.get("memory", {})),
        context=ContextConfig(**raw.get("context", {})),
        heartbeat=HeartbeatConfig(**raw.get("heartbeat", {})),
        safety=SafetyConfig(**raw.get("safety", {})),
    )
