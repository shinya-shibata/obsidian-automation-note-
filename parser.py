import re
import yaml
from pathlib import Path
from typing import Dict, List, Any

def parse_markdown_file(file_path: Path) -> Dict[str, Any]:
    """
    Markdownファイルを読み込み、Front Matter(パターン1)や、
    特定のセクション/行(パターン2や問い)をパースする。
    """
    content = ""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"警告: ファイル {file_path.name} の読み込みに失敗しました: {e}")
        return {"keywords": [], "notes": [], "unsolved_questions": []}

    keywords = []
    notes = []
    unsolved_questions = []

    # 1. Front Matterのパース (パターン1)
    # --- で囲まれた部分を抽出
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter_match:
        try:
            fm_data = yaml.safe_load(frontmatter_match.group(1))
            if isinstance(fm_data, dict):
                # keywordsの抽出
                kws = fm_data.get("keywords", [])
                if isinstance(kws, list):
                    keywords.extend([str(k) for k in kws])
                elif isinstance(kws, str):
                    keywords.append(kws)
        except Exception as e:
            print(f"警告: {file_path.name} の Front Matter 解析に失敗しました: {e}")

    # 2. セクション箇条書き形式 (パターン2) と 未解決の問いの抽出 (機能2)
    lines = content.splitlines()
    in_target_section = False

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # 未解決問題 (?- から始まる行)
        if stripped_line.startswith("?-"):
            # 例: "?- 量子力学の〜" から "量子力学の〜" を抽出
            question_text = stripped_line[2:].strip()
            if question_text:
                unsolved_questions.append(question_text)

        # パターン2のセクション判定
        if stripped_line.startswith("## 印象に残ったメモ"):
            in_target_section = True
            continue
        elif stripped_line.startswith("##") or stripped_line.startswith("#"):
            # 別のセクションに入ったらターゲットセクションを抜ける
            in_target_section = False

        if in_target_section:
            # 箇条書きを抽出
            if stripped_line.startswith("- ") or stripped_line.startswith("* "):
                note_text = stripped_line[2:].strip()
                if note_text:
                    notes.append(note_text)

    return {
        "keywords": keywords,
        "notes": notes,
        "unsolved_questions": unsolved_questions
    }

def extract_all_unsolved_questions(vault_dir: Path) -> List[str]:
    """
    Vault内のすべてのMarkdownファイルから未解決の問いをスキャンする
    """
    all_questions = set()
    # 99_System フォルダ自体はスキャンから除外
    for file_path in vault_dir.glob("**/*.md"):
        if "99_System" in file_path.parts:
            continue
        parsed = parse_markdown_file(file_path)
        for q in parsed["unsolved_questions"]:
            all_questions.add(q)
    return list(all_questions)
