import time
import random
from pathlib import Path
from config import (
    init_vault_structure, QUESTIONS_DIR, ANSWERS_DIR, BRAINSTORMING_DIR,
    PROMPT_TEMPLATE_PATH, UNSOLVED_QUESTIONS_PATH, SYSTEM_DIR
)
from parser import parse_markdown_file, extract_all_unsolved_questions
from gemini_client import generate_answer, generate_new_theory, integrate_theories
from arxiv_client import search_arxiv

def process_questions():
    """
    機能1: 質問・回答の自動処理とクレンジング
    """
    print("\n=== 機能1: 質問・回答の自動処理を開始 ===")
    
    # テンプレートの読み込み
    if not PROMPT_TEMPLATE_PATH.exists():
        init_vault_structure()
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    # 質問ファイルの探索
    question_files = list(QUESTIONS_DIR.glob("*.md"))
    if not question_files:
        print("質問ファイル (01_Questions/*.md) が見つかりませんでした。")
        return

    for q_file in question_files:
        content = q_file.read_text(encoding="utf-8").strip()
        if not content:
            print(f"スキップ: {q_file.name} はすでに空（クレンジング済み）です。")
            continue

        print(f"質問処理中: {q_file.name}...")
        try:
            # Geminiで回答生成
            answer, model = generate_answer(content, template)
            
            # 回答の書き出し
            ans_file = ANSWERS_DIR / q_file.name
            ans_content = f"# 質問内容\n\n{content}\n\n---\n\n# Geminiからの回答\n\n{answer}\n\n---\n*使用したAIモデル: {model}*\n"
            ans_file.write_text(ans_content, encoding="utf-8")
            print(f"回答を保存しました (使用モデル: {model}): {ans_file.name}")

            # 元ファイルのクレンジング (ファイルは残すが中身を空にする)
            q_file.write_text("", encoding="utf-8")
            print(f"クレンジング完了: {q_file.name} を空にしました。")

        except Exception as e:
            print(f"エラー: {q_file.name} の処理中に不具合が発生しました: {e}")

def pool_unsolved_questions():
    """
    機能2: 未解決問題の自動プール
    """
    print("\n=== 機能2: 未解決問題の自動プールを開始 ===")
    questions = extract_all_unsolved_questions(QUESTIONS_DIR.parent)
    if not questions:
        print("?- 記号で始まる未解決の問いは見つかりませんでした。")
        return

    # 重複を排除しつつ、既存の問いを読み込む
    existing_questions = set()
    if UNSOLVED_QUESTIONS_PATH.exists():
        content = UNSOLVED_QUESTIONS_PATH.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("- "):
                existing_questions.add(line_str[2:])

    # マージ
    all_questions = existing_questions.union(set(questions))

    # 保存
    unsolved_content = "# 未解決の問いのプール (問いのデータベース)\n\n"
    unsolved_content += "※ Vault内のノートから自動抽出された未解決の問題です。\n\n"
    for q in sorted(list(all_questions)):
        unsolved_content += f"- {q}\n"

    UNSOLVED_QUESTIONS_PATH.write_text(unsolved_content, encoding="utf-8")
    print(f"未解決の問いをプールしました ({len(all_questions)}件): {UNSOLVED_QUESTIONS_PATH.name}")

def generate_theories_from_notes():
    """
    機能3: 印象に残ったメモ・キーワードからの新理論生成
    """
    print("\n=== 機能3: 新理論の自動生成を開始 ===")
    
    brain_files = list(BRAINSTORMING_DIR.glob("*.md"))
    all_keywords = []
    all_notes = []

    for b_file in brain_files:
        # 新理論として生成されたファイル(新理論_xxx.md)自体はパース対象外
        if b_file.name.startswith("新理論_"):
            continue
            
        parsed = parse_markdown_file(b_file)
        all_keywords.extend(parsed["keywords"])
        all_notes.extend(parsed["notes"])

    if not all_keywords and not all_notes:
        print("パース可能なキーワードまたは印象に残ったメモが見つかりませんでした。")
        return

    print(f"パース完了: キーワード {len(all_keywords)}件, 印象に残ったメモ {len(all_notes)}件 取得しました。")

    all_keywords = list(set(all_keywords))
    all_notes = list(set(all_notes))

    print("Geminiに接続し、新理論を構築中...")
    try:
        # キーワードから最大5つ、メモから最大3つを組み合わせて送信
        theory, model = generate_new_theory(all_keywords[:5], all_notes[:3])
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        theory_file = BRAINSTORMING_DIR / f"新理論_{timestamp}.md"
        theory_file.write_text(theory + f"\n\n---\n*使用したAIモデル: {model}*\n", encoding="utf-8")
        
        print(f"新しい理論が自動生成されました！ (使用モデル: {model}): {theory_file.name}")
    except Exception as e:
        print(f"理論生成エラー: {e}")

def run_arxiv_pipeline():
    """
    機能4: arXiv連携と自動要約 (拡張機能)
    """
    print("\n=== 機能4: arXiv自動検索＆要約 (拡張機能) を開始 ===")
    query_sources = []
    
    if UNSOLVED_QUESTIONS_PATH.exists():
        content = UNSOLVED_QUESTIONS_PATH.read_text(encoding="utf-8")
        questions = [line[2:].strip() for line in content.splitlines() if line.strip().startswith("- ")]
        if questions:
            query_sources.extend(questions)

    if not query_sources:
        query_sources = ["Self-organization", "Quantum brain biology", "Complexity scaling laws"]

    selected_query = random.choice(query_sources)
    print(f"セレンディピティ: 問い/キーワード '{selected_query}' に基づき、arXivを調査します。")

    papers = search_arxiv(selected_query, max_results=2)
    if not papers:
        print("arXivから論文情報を見つけられませんでした。")
        return

    arxiv_summary_path = SYSTEM_DIR / "arxiv_summary.md"
    arxiv_content = f"# arXiv 学術検索サマリー\n\n"
    arxiv_content += f"**調査クエリ**: {selected_query}\n"
    arxiv_content += f"※ セレンディピティ機能により自動実行された検索結果です。\n\n---\n\n"

    for idx, paper in enumerate(papers, 1):
        print(f"論文 [{idx}] の3行要約と貢献度スコアリングを生成中...")
        gemini_prompt = f"""
以下の学術論文の英語タイトルとアブストラクトを読み込み、日本語で「3行要約」と「貢献度スコアリング(A〜C)」を作成してください。

【論文情報】
タイトル: {paper['title']}
アブストラクト: {paper['abstract']}

【出力ルール】
1. **3行要約**:
   - 1行目: 課題の記述
   - 2行目: アプローチの記述
   - 3行目: インパクトや可能性の記述
2. **貢献度スコア**:
   - A（極めて革新的）、B（興味深い・期待）、C（限定的）から選択。

日本語でロジカルに出力してください。
"""
        from gemini_client import generate_content_with_fallback
        evaluation, used_model = generate_content_with_fallback(gemini_prompt)

        arxiv_content += f"## {idx}. {paper['title']}\n"
        arxiv_content += f"- **著者**: {paper['authors']}\n"
        arxiv_content += f"- **発行年**: {paper['published']}\n"
        arxiv_content += f"- **リンク**: {paper['pdf_url']}\n\n"
        arxiv_content += f"### Gemini 評価 & 3行サマリー (使用モデル: {used_model})\n\n{evaluation}\n\n"
        arxiv_content += "---\n\n"

    # 追記または新規作成
    if arxiv_summary_path.exists():
        existing = arxiv_summary_path.read_text(encoding="utf-8")
        arxiv_summary_path.write_text(existing + "\n\n" + arxiv_content, encoding="utf-8")
    else:
        arxiv_summary_path.write_text(arxiv_content, encoding="utf-8")

    print(f"arXiv自動調査結果を保存しました: {arxiv_summary_path.name}")

def run_theory_integration_pipeline():
    """
    機能5: 2つの理論・概念の構造的統合
    """
    print("\n=== 機能5: 2つの異なる理論の構造的統合を開始 ===")
    print("全く異なる2つの理論・概念を構造的に統合し、新しい学術的・分析的思考フレームワークを創出します。")
    
    theory_a = input("【理論A】を入力してください: ").strip()
    if not theory_a:
        print("理論Aが入力されなかったため、処理を中断します。")
        return
        
    theory_b = input("【理論B】を入力してください: ").strip()
    if not theory_b:
        print("理論Bが入力されなかったため、処理を中断します。")
        return

    print("\n適用する統合アプローチを選択してください:")
    print("1: 構造的同型性発見型")
    print("2: 視点・レンズ適用型")
    print("3: 弁証法（矛盾解消）型")
    print("4: アノマリーブレイクスルー型")
    print("5: 自動最適化 (推奨)")
    app_choice = input("選択 (デフォルト: 5): ").strip()
    
    approaches = {
        "1": "1. 構造的同型性発見型",
        "2": "2. 視点・レンズ適用型",
        "3": "3. 弁証法（矛盾解消）型",
        "4": "4. アノマリーブレイクスルー型",
        "5": "5. 自動最適化"
    }
    approach = approaches.get(app_choice, "5. 自動最適化")
    
    print(f"\nアプローチ「{approach}」を用いてGemini APIで構造的統合思考を実行中...")
    try:
        integrated_theory, model = integrate_theories(theory_a, theory_b, approach)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        integrated_file = BRAINSTORMING_DIR / f"統合理論_{timestamp}.md"
        integrated_file.write_text(integrated_theory + f"\n\n---\n*使用したAIモデル: {model}*\n", encoding="utf-8")
        
        print(f"構造的統合理論が創出されました！ (使用モデル: {model}): {integrated_file.name}")
    except Exception as e:
        print(f"理論統合エラー: {e}")

def main():
    print("====================================================")
    print("  Obsidian × Gemini API 自己組織化ナレッジシステム")
    print("====================================================")
    
    init_vault_structure()
    
    while True:
        print("\n--- 実行メニュー ---")
        print("1: 【フェーズ1】質問回答処理 & クレンジング")
        print("2: 【フェーズ2】未解決問題の自動プール")
        print("3: 【フェーズ3】キーワード・メモからの新理論自動生成")
        print("4: 【フェーズ4】arXiv検索＆要約＆スコアリング")
        print("5: 【フェーズ5】2つの異なる理論の構造的統合 (新機能)")
        print("6: すべてを一括実行")
        print("0: 終了")
        
        choice = input("選択してください (0-6): ").strip()
        
        if choice == "1":
            process_questions()
        elif choice == "2":
            pool_unsolved_questions()
        elif choice == "3":
            generate_theories_from_notes()
        elif choice == "4":
            run_arxiv_pipeline()
        elif choice == "5":
            run_theory_integration_pipeline()
        elif choice == "6":
            process_questions()
            pool_unsolved_questions()
            generate_theories_from_notes()
            run_arxiv_pipeline()
            run_theory_integration_pipeline()
            print("\n一括実行が完了しました！")
        elif choice == "0":
            print("プログラムを終了します。")
            break
        else:
            print("無効な選択です。")

if __name__ == "__main__":
    main()
