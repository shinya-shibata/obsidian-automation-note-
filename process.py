import os
import time
import glob
import re
from google import genai
from google.genai import types
from google.genai.errors import APIError

# クライアントの初期化
# 環境変数 GEMINI_API_KEY が設定されていれば、api_keyの指定は不要です。
# 必要に応じて、直接 api_key="YOUR_API_KEY" を指定してください。
client = genai.Client()

# Obsidianのフォルダパス（ご自身の環境に合わせて書き換えてください）
OBSIDIAN_FOLDER = "C:/Users/YourName/Documents/Obsidian/VaultName/Questions" 
# 念のための自動バックアップ先フォルダ
BACKUP_FOLDER = "C:/Users/YourName/Documents/Obsidian/VaultName/Questions_Backup"

def process_paragraph(paragraph: str) -> str:
    """
    1つの段落（または箇条書き）を解析し、Geminiに問い合わせて回答を追記します。
    """
    text = paragraph.strip()
    if not text:
        return paragraph

    # 箇条書き記号（- や *、数字の箇条書きなど）を正規表現で検出して分解
    match = re.match(r"^(\s*[-*+]\s+|\s*\d+\.\s+)(.*)$", text, re.DOTALL)
    
    if match:
        prefix = match.group(1)       # 行頭の箇条書き記号（例: "- "）
        content = match.group(2).strip() # 質問の本文
    else:
        prefix = "- "                 # 箇条書き記号がない場合はデフォルトで付与
        content = text

    # 二重処理防止：既に「回答:」や「Answer:」が含まれている場合はスキップ
    if "\n" in content and ("回答:" in content or "Answer:" in content or "**回答:**" in content):
        print(f"スキップ（既に回答が存在する可能性があります）: {content[:20]}...")
        return paragraph

    print(f"Geminiに問い合わせ中: {content[:30]}...")
    
    # 質問文の構築
    prompt = content + "\n\n指示文：簡潔に専門的に解説してください。"
    
    # レート制限（429エラーなど）に対応するためのリトライ処理
    max_retries = 3
    answer = ""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=2048,
                    ),
                ),
            )
            answer = response.text.strip()
            break
        except APIError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 15
                print(f"APIエラーが発生しました。{wait_time}秒後に再試行します: {e}")
                time.sleep(wait_time)
            else:
                print(f"エラー: 最大試行回数を超えました。元の文章を維持します。: {e}")
                return paragraph
        except Exception as e:
            print(f"予期しないエラーが発生しました: {e}")
            return paragraph

    if not answer:
        return paragraph

    # Obsidianで箇条書きの下に綺麗に配置するため、回答の各行に半スペース4つのインデントを適用
    indented_answer = "\n".join([f"    {line}" for line in answer.split("\n")])
    
    # 元の箇条書きの下に、インデント下げした箇条書きとして回答を追記
    new_paragraph = f"{prefix}{content}\n    - **回答:**\n{indented_answer}"
    return new_paragraph

def process_obsidian_notes():
    """
    指定されたObsidianフォルダ内のマークダウンファイルを読み込み、
    段落ごとに分割して処理し、元のファイルに上書き保存します。
    """
    # バックアップフォルダの自動作成
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    
    note_paths = glob.glob(os.path.join(OBSIDIAN_FOLDER, "*.md"))
    
    if not note_paths:
        print(f"指定されたフォルダにMarkdownファイルが見つかりません: {OBSIDIAN_FOLDER}")
        return

    for note_path in note_paths:
        base_name = os.path.basename(note_path)
        print(f"\n=== ファイル処理開始: {base_name} ===")
        
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                print(f"空ファイルのためスキップします: {base_name}")
                continue
                
            # 処理前にバックアップを作成（安全のため）
            backup_path = os.path.join(BACKUP_FOLDER, base_name)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 改行コードを統一した上で、空行（\n\n）を基準に段落を分割
            content_normalized = content.replace("\r\n", "\n")
            paragraphs = content_normalized.split("\n\n")
            
            new_paragraphs = []
            for para in paragraphs:
                if para.strip():
                    new_para = process_paragraph(para)
                    new_paragraphs.append(new_para)
                    # 連続リクエストによるレート制限を避けるため、各段落間で少し待機
                    time.sleep(2)
                else:
                    new_paragraphs.append(para)
                    
            # 処理後の段落を空行で再結合して、元のファイルに上書き
            new_content = "\n\n".join(new_paragraphs)
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            print(f"処理完了（上書き保存完了）: {base_name}")
            
        except Exception as e:
            print(f"ファイル処理中にエラーが発生しました ({note_path}): {e}")

if __name__ == "__main__":
    process_obsidian_notes()
