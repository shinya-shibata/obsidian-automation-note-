import os
import time
import glob
import re
import shutil
from google import genai
from google.genai import types
from google.genai.errors import APIError

client = genai.Client(api_key="your API key")

# 【新しい保存場所の設計】
# 質問を書き込むフォルダ（処理待ち）
QUEUE_FOLDER = "C:/Users/user/Documents/Obsidian Vault/01_Questions_Queue" 
# 処理が完了したノートの自動移動先（処理済み）
ARCHIVE_FOLDER = "C:/Users/user/Documents/Obsidian Vault/02_Questions_Archive"

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
    prompt = content + "\n\n指示文：の内容をわかりやすく解説してください。"
    
    max_retries = 3
    answer = ""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
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
                return f"{prefix}{content}\n    - **エラー (API):** {e}"
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return f"{prefix}{content}\n    - **エラー (システム):** {e}"

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
                
            # 改行コードを統一
            content_normalized = content.replace("\r\n", "\n")
            
            # 【改善】空行がなくても箇条書き記号（- や *、数字など）で自動的に質問を分割する
            lines = content_normalized.split("\n")
            paragraphs = []
            current_para = []

            for line in lines:
                # 空行の場合は、現在の質問の区切りとして処理
                if not line.strip():
                    if current_para:
                        paragraphs.append("\n".join(current_para))
                        current_para = []
                    continue
                
                # 行頭が箇条書き記号（- , * , + , 1. など）で始まっているか判定
                is_bullet = re.match(r"^(\s*[-*+]\s+|\s*\d+\.\s+)", line)
                
                if is_bullet:
                    # すでに前の質問文が溜まっている場合は、それを1つの質問として保存
                    if current_para:
                        paragraphs.append("\n".join(current_para))
                    current_para = [line]
                else:
                    # 箇条書き記号がない行（複数行にわたる質問など）は、現在の質問の続きとして結合
                    if current_para:
                        current_para.append(line)
                    else:
                        current_para = [line]
            
            if current_para:
                paragraphs.append("\n".join(current_para))
            
            new_paragraphs = []
            for para in paragraphs:
                if para.strip():
                    new_para = process_paragraph(para)
                    new_paragraphs.append(new_para)
                    time.sleep(2)
                else:
                    new_paragraphs.append(para)
                    
            # 同名ファイルが移動先にある場合の競合防止（必要に応じてファイル名をユニークに）
            archive_path = os.path.join(ARCHIVE_FOLDER, base_name)
            if os.path.exists(archive_path):
                # 重複回避のためタイムスタンプを付与
                name, ext = os.path.splitext(base_name)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                archive_path = os.path.join(ARCHIVE_FOLDER, f"{name}_{timestamp}{ext}")

            # 回答を追記した内容をアーカイブフォルダ（移動先）に直接保存
            new_content = "\n\n".join(new_paragraphs)
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # 元のファイルは消さずに、中身（質問事項）だけを空（白紙）にして上書き保存
            with open(note_path, "w", encoding="utf-8") as f:
                f.write("")
                
            print(f"処理完了（アーカイブ保存先: {os.path.basename(archive_path)}、元のファイルをクリアしました）")
            
        except Exception as e:
            print(f"ファイル処理中にエラーが発生しました ({note_path}): {e}")

if __name__ == "__main__":
    process_obsidian_notes()
