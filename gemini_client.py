import time
from google import genai
from config import GEMINI_API_KEY

# APIクライアントの初期化 (最新の google-genai SDKを使用)
client = genai.Client(api_key=GEMINI_API_KEY)

# 無料枠での安全なAPI呼び出しのためのウェイト (RPM制限対策)
# 無料枠: 15 RPM => 4秒以上の間隔を自動で確保
LAST_CALL_TIME = 0.0

def safe_api_call(func, *args, **kwargs):
    global LAST_CALL_TIME
    elapsed = time.time() - LAST_CALL_TIME
    if elapsed < 4.0:
        time.sleep(4.0 - elapsed)
    
    try:
        response = func(*args, **kwargs)
        LAST_CALL_TIME = time.time()
        return response
    except Exception as e:
        print(f"Gemini API 呼び出しエラー: {e}")
        raise e

def generate_answer(question: str, template: str) -> str:
    """
    質問に対してテンプレートと結合してGeminiで回答を生成する (機能1)
    """
    prompt = f"""
以下のテンプレートに基づいて、質問に対する知的で実用的な回答を生成してください。

【回答テンプレートの構成】
{template}

【質問内容】
{question}
"""
    response = safe_api_call(
        client.models.generate_content,
        model="gemini-2.5-flash",  # 無料枠推奨の最新モデル
        contents=prompt
    )
    return response.text

def generate_new_theory(keywords: list[str], notes: list[str]) -> str:
    """
    キーワードやメモを掛け合わせ、自動的に新理論を生成する (機能3)
    """
    kws_str = "\n".join([f"- {kw}" for kw in keywords])
    notes_str = "\n".join([f"- {n}" for n in notes])

    prompt = f"""
あなたは、異なる分野のアイデアや概念を組み合わせ、画期的でアヴァンギャルドな新しい科学的・哲学的理論を提唱する天才研究者です。

以下の「キーワード」および「印象に残ったメモ」をもとに、これらを高次元で結合した「新しい理論」を作成してください。

【インプットデータ】
{f"■ キーワード:\n{kws_str}" if keywords else ""}
{f"■ 印象に残ったメモ:\n{notes_str}" if notes else ""}

【理論生成ルール】
1. 理論に魅力的でキャッチーな「理論名（タイトル）」を付与してください。
2. 理論の核心となるコンセプトを、一般人でもワクワクするが、専門的にも緻密なロジックで説明してください。
3. この理論に関連する「実在の科学的キーワード、先行研究の検索クエリ候補」を5つ挙げてください。
4. この理論に対する「想定される学術的・技術的な批判、反論、または限界」をセットで3つ出力してください。

理論は、Markdown形式で美しく整形して出力してください。
"""
    response = safe_api_call(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def integrate_theories(theory_a: str, theory_b: str, approach: str) -> str:
    """
    全く異なる2つの理論を構造的に統合し、新しい学術的・分析的思考フレームワークを創出する (新機能5)
    """
    prompt = f"""あなたは異分野の概念を融合させ、新たなパラダイムを創出することに長けた、世界最高峰の科学哲学者であり理論モデラーです。
提示された2つの異なる理論（または概念・メモ）の根底にある抽象的な構造を見抜き、それらを論理的・数理的に統合した「新しい思考フレームワーク（新理論）」を構築することがあなたの任務です。

評価の甘い安易な結合ではなく、両者の「前提の衝突」や「限界点」を厳しく批判的に検証した上で、それらを高次元で解消（アウフヘーベン）する、学術的に堅牢なプロトタイプ（仮説）を提示してください。

【出力時の絶対ルール】
1. 指定された思考ステップ（Step 1 〜 Step 5）を絶対に省略せず、段階的に思考を展開すること。
2. 専門用語（例: 構造的同型性、写像、エントロピー等）は文脈に即して厳密に使用すること。
3. 最後に、理論の堅牢性を担保するため、以下の「検証・批判セクション」を自動的に付加すること。
   - 「この理論に関連する実在の科学的キーワード、先行研究の検索クエリ候補」を5つ挙げる。
   - 「この理論に対する想定される批判・反論」や「技術的な限界」をセットで3つ挙げる。

# 入力情報
- 【理論A】：{theory_a}
- 【理論B】：{theory_b}

# 適用する統合アプローチ（以下の【 】から1つを選択、または「自動最適化」と指定してください）
【選択肢：1. 構造的同型性発見型 / 2. 視点・レンズ適用型 / 3. 弁証法（矛盾解消）型 / 4. アノマリーブレイクスルー型 / 5. 自動最適化】
アプローチ：{approach}

---

# 思考プロセス（以下のステップ順に段階的に出力してください）

## Step 1: 構造の抽出（抽象化）
選択したアプローチに基づき、各理論から具象的な対象（言葉・現象）を取り払い、コアとなる「構造」「変数」「因果関係のパターン」を箇条書きで抽象化してください。

## Step 2: 同型性（アナロジー）と対応関係の発見
理論Aの概念要素と、理論Bの概念要素で「数理的・論理的に同じ役割を果たしているもの」をペアリング（写像）し、Markdownの対比表を作成してください。

## Step 3: 前提の対立と矛盾の特定
2つの理論を接合する際に生じる「前提条件の矛盾」や「視点の食い違い（限界点）」を明確に洗い出してください。

## Step 4: 上位概念（メタフレームワーク）による統合
Step 3で抽出した矛盾を解消し、両方の理論が「ある特殊な条件下での極限状態」として説明できるような、より上位の統合モデル（または新しい公理）を提案してください。

## Step 5: 新理論の命名とコア命題の策定
1. **新理論の名称**（キャッチーで本質を表すもの）
2. **コア命題（Core Thesis）**：1〜2文で表す新しい法則や命題
3. **数式またはロジックモデルのイメージ**：概念間の関係を示す簡略化した関係式またはロジックフロー
4. **この新理論によって解明できる「既存理論では説明できなかった現象」の具体例**

---

# 検証・批判セクション

## 1. 関連する実在の科学的キーワード・先行研究検索クエリ（5選）
※この仮説を深掘り・検証するために役立つ、arXivやGoogle Scholarで検索可能なクエリ。

## 2. 想定される批判・反論および技術的限界（3選）
※この理論が直面するであろう論理的破綻の可能性や、実証における限界。
"""
    response = safe_api_call(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text
