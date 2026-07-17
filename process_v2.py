import os
import time
import glob
import re
import shutil
from google import genai
from google.genai import types
from google.genai.errors import APIError

client = genai.Client()

# 【新しい保存場所の設計】
# 質問を書き込むフォルダ（処理待ち）
QUEUE_FOLDER = "C:/Users/YourName/Documents/Obsidian/VaultName/01_Questions_Queue" 
# 処理が完了したノートの自動移動先（処理済み）
ARCHIVE_FOLDER = "C:/Users/YourName/Documents/Obsidian/VaultName/02_Questions_Archive"

def process_paragraph(paragraph: str) -> str:
    """1つの段落を解析し、Geminiに問い合わせて回答を追記します。"""
    text = paragraph.strip()
    if not text:
        return paragraph

    match = re.match(r"^(\s*[-*+]\s+|\s*\d+\.\s+)(.*)$", text, re.DOTALL)
    if match:
        prefix = match.group(1)
        content = match.group(2).strip()
    else:
        prefix = "- "
        content = text

    # すでに回答が追記されている場合はスキップ
    if "\n" in content and ("回答:" in content or "Answer:" in content or "**回答:**" in content):
        return paragraph

    print(f"Geminiに問い合わせ中: {content[:30]}...")
    prompt = content + "\n\n指示文：簡潔に専門的に解説してください。"
    
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
                print(f"エラー: 最大試行回数を超えました。: {e}")
                return paragraph
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return paragraph

    if not answer:
        return paragraph

    indented_answer = "\n".join([f"    {line}" for line in answer.split("\n")])
    new_paragraph = f"{prefix}{content}\n    - **回答:**\n{indented_answer}"
    return new_paragraph

def process_obsidian_notes():
    # フォルダが存在しない場合は作成
    os.makedirs(QUEUE_FOLDER, exist_ok=True)
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
    
    # Queueフォルダ内の未処理のMarkdownファイルを取得
    note_paths = glob.glob(os.path.join(QUEUE_FOLDER, "*.md"))
    
    if not note_paths:
        print(f"処理待ちのノートはありません（{QUEUE_FOLDER} 内は空です）")
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

            content_normalized = content.replace("\r\n", "\n")
            paragraphs = content_normalized.split("\n\n")
            
            new_paragraphs = []
            for para in paragraphs:
                if para.strip():
                    new_para = process_paragraph(para)
                    new_paragraphs.append(new_para)
                    time.sleep(2)
                else:
                    new_paragraphs.append(para)
                    
            # 回答を追記した内容を元のファイルに上書き保存
            new_content = "\n\n".join(new_paragraphs)
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # 【効率化のポイント】処理済みのフォルダへファイルを移動
            archive_path = os.path.join(ARCHIVE_FOLDER, base_name)
            
            # 同名ファイルが移動先にある場合の競合防止（必要に応じてファイル名をユニークに）
            if os.path.exists(archive_path):
                # 重複回避のためタイムスタンプを付与
                name, ext = os.path.splitext(base_name)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                archive_path = os.path.join(ARCHIVE_FOLDER, f"{name}_{timestamp}{ext}")

            shutil.move(note_path, archive_path)
            print(f"処理完了（移動先: {os.path.basename(archive_path)}）")
            
        except Exception as e:
            print(f"ファイル処理中にエラーが発生しました ({note_path}): {e}")

if __name__ == "__main__":
    process_obsidian_notes()
