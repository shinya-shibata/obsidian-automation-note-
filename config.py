import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# APIキーの取得
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("エラー: 環境変数 'GEMINI_API_KEY' が設定されていません。.env ファイルを確認してください。", file=sys.stderr)
    sys.exit(1)

# Vaultディレクトリの設定
# デフォルトはカレントディレクトリの 'Vault' フォルダ。
# 環境変数 'OBSIDIAN_VAULT_PATH' で任意の場所にオーバーライド可能です。
VAULT_DIR = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./Vault")).resolve()

# 各種フォルダパスの解決
QUESTIONS_DIR = VAULT_DIR / "01_Questions"
ANSWERS_DIR = VAULT_DIR / "02_Answers"
BRAINSTORMING_DIR = VAULT_DIR / "03_Brainstorming"
TEMPLATES_DIR = VAULT_DIR / "04_Templates"
SYSTEM_DIR = VAULT_DIR / "99_System"

# テンプレートファイルのパス
PROMPT_TEMPLATE_PATH = TEMPLATES_DIR / "prompt_template.md"

# 未解決問題集約ファイルのパス
UNSOLVED_QUESTIONS_PATH = SYSTEM_DIR / "unsolved_questions.md"

# フォルダが存在しない場合に自動生成する
def init_vault_structure():
    """Obsidianのディレクトリ構造を自動的に初期化します"""
    for folder in [QUESTIONS_DIR, ANSWERS_DIR, BRAINSTORMING_DIR, TEMPLATES_DIR, SYSTEM_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # デフォルトの思考整理テンプレートを作成
    if not PROMPT_TEMPLATE_PATH.exists():
        PROMPT_TEMPLATE_PATH.write_text(
            "# 思考整理プロンプトテンプレート\n\n"
            "あなたはユーザーの思考の壁打ち相手であり、卓越した知識を持つAI研究パートナーです。\n"
            "以下の質問に対して、ただ事実を答えるだけでなく、以下の構成で回答してください。\n\n"
            "1. **要約**: 質問の核心を一言で整理する\n"
            "2. **詳細回答**: 科学的・論理的根拠に基づく深い洞察を交えて解説する\n"
            "3. **さらなる問いの提案**: このテーマを深めるための、次に考えるべき「問い」を2つ提示する\n",
            encoding="utf-8"
        )
