# ====================================================================
# workspace/manager.py — ワークスペース .md ファイル管理
# ====================================================================
#
# 【このファイルは何？】
# workspace/ フォルダにある .md ファイル群を読み書きする。
# これらのファイルが「エージェントの性格と長期記憶」を形成する。
#
# 【ファイル一覧と役割】
# SOUL.md      → エージェントの性格・行動原則
# AGENTS.md    → 操作マニュアル（自分はどんなツールを使えるか）
# USER.md      → ユーザー情報（名前、専門分野、好み）
# IDENTITY.md  → 名前・アイコン（自己紹介用）
# TOOLS.md     → 環境メモ（STAR-CCM+のパス等）
# MEMORY.md    → 長期記憶（過去の経験・学んだこと）
# HEARTBEAT.md → 定期チェック項目
#
# 【どう使う？】
# ws = WorkspaceManager(config)
# soul = ws.read_soul()  → SOUL.md の内容を返す
# ws.append_memory("新しい学び")  → MEMORY.md に追記
# ====================================================================

from pathlib import Path
from datetime import datetime

# ワークスペースを構成するファイルと説明の一覧
WORKSPACE_FILES = {
    "SOUL.md":      "エージェントの性格",
    "AGENTS.md":    "操作マニュアル",
    "USER.md":      "ユーザー情報",
    "IDENTITY.md":  "名前・アイコン",
    "TOOLS.md":     "環境メモ",
    "MEMORY.md":    "長期記憶",
    "HEARTBEAT.md": "定期チェック項目",
}


class WorkspaceManager:
    """ワークスペース .md ファイルを管理する。"""

    def __init__(self, config):
        self.workspace_dir = Path(config.workspace.dir)
        self.daily_log_dir = Path(config.memory.daily_log_dir)
        # フォルダがなければ作成する
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.daily_log_dir.mkdir(parents=True, exist_ok=True)
        # デフォルトテンプレートをコピーする
        self._initialize_defaults()

    def _initialize_defaults(self):
        """ファイルがなければデフォルトテンプレートをコピーする。"""
        defaults_dir = Path(__file__).parent / "defaults"
        for filename in WORKSPACE_FILES:
            target = self.workspace_dir / filename
            if not target.exists():
                template = defaults_dir / filename
                if template.exists():
                    # テンプレートが存在すればコピーする
                    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
                else:
                    # テンプレートがなければ空ファイルを作る
                    target.write_text(f"# {filename}\n\n（未設定）\n", encoding="utf-8")

    def read_file(self, filename):
        """指定した .md ファイルの内容を返す。存在しない場合は空文字。"""
        path = self.workspace_dir / filename
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_soul(self):       return self.read_file("SOUL.md")
    def read_agents(self):     return self.read_file("AGENTS.md")
    def read_user(self):       return self.read_file("USER.md")
    def read_memory(self):     return self.read_file("MEMORY.md")
    def read_heartbeat(self):  return self.read_file("HEARTBEAT.md")

    def build_system_context(self):
        """全 .md を結合してシステムプロンプト用コンテキストを作る。"""
        sections = []
        for filename, desc in WORKSPACE_FILES.items():
            content = self.read_file(filename)
            if content.strip():
                sections.append(f"=== {filename} ({desc}) ===\n{content}")
        return "\n\n".join(sections)

    def append_memory(self, text):
        """MEMORY.md に追記する。タイムスタンプ付き。"""
        path = self.workspace_dir / "MEMORY.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n### {timestamp}\n{text}\n")

    def write_daily_log(self, content):
        """memory/YYYY-MM-DD.md に日次ログを追記する。"""
        today = datetime.now().strftime("%Y-%m-%d")
        path = self.daily_log_dir / f"{today}.md"
        timestamp = datetime.now().strftime("%H:%M")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## {timestamp}\n{content}\n")
