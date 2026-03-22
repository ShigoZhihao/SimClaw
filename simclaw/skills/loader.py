# ====================================================================
# skills/loader.py — SKILL.md を読み込んでシステムプロンプトに注入
# ====================================================================
#
# 【このファイルは何？】
# skills/ フォルダの SKILL.md を読み込んで、
# エージェントの専門知識としてシステムプロンプトに追加する。
#
# 【SKILL.md の形式（YAMLフロントマター + Markdown）】
# ---
# name: star-ccm-basics
# description: "STAR-CCM+基本操作スキル"
# ---
# ## 使い方
# ...
#
# 【どう使う？】
# loader = SkillLoader(config)
# skill_text = loader.build_skill_context()
# system_prompt += "\n\n--- Skills ---\n" + skill_text
# ====================================================================

from pathlib import Path


class SkillLoader:
    """スキルディレクトリから SKILL.md を読み込む。"""

    def __init__(self, config):
        # 複数のスキルディレクトリに対応する
        self.skill_dirs = [Path(d) for d in config.skills.dirs]

    def load_all(self):
        """全スキルを読み込んでリストで返す。

        戻り値:
            [{"name": ..., "description": ..., "content": ...}] のリスト
        """
        skills = []
        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                continue
            # 各サブフォルダの SKILL.md を探す
            for sub in sorted(skill_dir.iterdir()):
                skill_file = sub / "SKILL.md"
                if not skill_file.exists():
                    continue
                try:
                    skill = self._load_skill_file(skill_file, sub.name)
                    if skill:
                        skills.append(skill)
                except Exception as e:
                    print(f"  スキル読込エラー: {skill_file} — {e}")
        return skills

    def _load_skill_file(self, skill_file, default_name):
        """1つの SKILL.md を読み込む。

        python-frontmatter がインストールされていれば YAMLメタデータを解析する。
        インストールされていなければ全文をコンテンツとして扱う。
        """
        raw_text = skill_file.read_text(encoding="utf-8")

        try:
            import frontmatter
            post = frontmatter.loads(raw_text)
            return {
                "name": post.get("name", default_name),
                "description": post.get("description", ""),
                "content": post.content,
            }
        except ImportError:
            # python-frontmatter が未インストールの場合は全文をそのまま使う
            return {
                "name": default_name,
                "description": "",
                "content": raw_text,
            }

    def build_skill_context(self):
        """全スキルをひとつの文字列に結合して返す。"""
        skills = self.load_all()
        if not skills:
            return ""
        return "\n\n".join(
            f"=== Skill: {s['name']} ===\n"
            + (f"{s['description']}\n\n" if s['description'] else "")
            + s['content']
            for s in skills
        )
