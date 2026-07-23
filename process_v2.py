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
    """
    1つの段落（または箇条書き）を解析し、Geminiに問い合わせて回答を追記します。
    最新モデルがクォータ制限（429）や混雑（503）に達している場合は、自動的に安定モデルに切り替えます。
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
        return paragraph

    # モデルの設定
    PRIMARY_MODEL = 'gemini-3.5-flash'
    BACKUP_MODEL = 'gemini-3.5-flash-lite'

    print(f"Geminiに問い合わせ中: {content[:30]}...")
    prompt = content + "\n\n指示文：の内容をわかりやすく解説してください。"
    
    max_retries = 3
    answer = ""
    for attempt in range(max_retries):
        # 1回目の試行は最新モデル、エラーが発生した場合はバックアップモデル（1.5-flash）を使用
        current_model = PRIMARY_MODEL if attempt == 0 else BACKUP_MODEL
        
        try:
            if attempt > 0:
                print(f"モデルを {current_model} に切り替えて再試行します...")
                
            response = client.models.generate_content(
                model=current_model,
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
                # クォータ制限や混雑時は、早めにバックアップモデルへ切り替えるため待機時間を短縮（5秒）
                wait_time = (attempt + 1) * 5
                print(f"APIエラーが発生しました。{wait_time}秒後にバックアップモデル({BACKUP_MODEL})で再試行します: {e}")
                time.sleep(wait_time)
            else:
                print(f"エラー: 最大試行回数を超えました。: {e}")
                return f"{prefix}{content}\n    - **エラー (API):** {e}"
        except Exception as e:
            print(f"予期しないエラーが発生しました: {e}")
            return f"{prefix}{content}\n    - **エラー (システム):** {e}"

    if not answer:
        return paragraph

    indented_answer = "\n".join([f"    {line}" for line in answer.split("\n")])
    new_paragraph = f"{prefix}{content}\n    - **回答:**\n{indented_answer}"
    return new_paragraph

def process_obsidian_notes():
    """
    指定されたObsidianフォルダ内のマークダウンファイルを読み込み、
    段落ごとに分割して処理し、元のファイルに上書き保存します。
    """
    # フォルダが存在しない場合は作成
    os.makedirs(QUEUE_FOLDER, exist_ok=True)
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
    
    # Queueフォルダ内の未処理のMarkdownファイルを取得
    note_paths = glob.glob(os.path.join(QUEUE_FOLDER, "*.md"))
    
    if not note_paths:
        print(f"処理待ちのノートはありません（{QUEUE_FOLDER} 内は空です）")
        return

    # 【音で通知】処理が開始したことを知らせる音 (ピピッ)
    try:
        import winsound
        winsound.Beep(2000, 100)
        winsound.Beep(2000, 100)
    except:
        pass

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

            # 【音で通知】回答が完了して保存されたことを知らせる音 (ピロリ〜ン)
            try:
                import winsound
                winsound.Beep(1200, 100)
                winsound.Beep(1600, 100)
                winsound.Beep(2000, 250)
            except:
                pass
            
        except Exception as e:
            print(f"ファイル処理中にエラーが発生しました ({note_path}): {e}")

if __name__ == "__main__":
    process_obsidian_notes()
