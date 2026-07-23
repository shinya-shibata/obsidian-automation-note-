<%*
/*
========================================================================
   Obsidian × Gemini 自己組織化ナレッジシステム (完全Obsidian完結版 JS)
========================================================================
   【概要】
   このスクリプトは、Obsidianの人気プラグイン「Templater」を使用し、
   Pythonなどの外部環境を一切使わずに、Obsidian内で完全に完結して
   Gemini APIとの連携（質問・未解決問題プール・新理論生成・arXiv検索・2理論統合）
   を高速に実行するためのものです。

   【事前準備】
   1. Obsidianの設定 -> コミュニティプラグイン -> 「Templater」をインストール＆有効化。
   2. 下記の「YOUR_GEMINI_API_KEY」をご自身のAPIキー（Google AI Studioから無料取得）に書き換えてください。
   3. 適当な新規ノート（例: 「自己組織化システム起動パネル」）を作成し、このコード全体を貼り付けます。
   4. 「Alt + E」などのショートカット、またはTemplaterの実行コマンドでこのテンプレートを展開すると、
      ポップアップメニューが立ち上がり、すべてのフェーズを実行できます。
*/

const GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"; // ★ここにご自身のGemini APIキーを入力してください

// 各種フォルダの定義
const VAULT_ROOT = "";
const QUESTIONS_DIR = "01_Questions";
const ANSWERS_DIR = "02_Answers";
const BRAINSTORMING_DIR = "03_Brainstorming";
const TEMPLATES_DIR = "04_Templates";
const SYSTEM_DIR = "99_System";

// フォルダ作成関数
async function ensureFolder(path) {
    if (!(await app.vault.adapter.exists(path))) {
        await app.vault.createFolder(path);
    }
}

// 初期ディレクトリ構造の確認
async function initStructure() {
    await ensureFolder(QUESTIONS_DIR);
    await ensureFolder(ANSWERS_DIR);
    await ensureFolder(BRAINSTORMING_DIR);
    await ensureFolder(TEMPLATES_DIR);
    await ensureFolder(SYSTEM_DIR);

    const templatePath = `${TEMPLATES_DIR}/prompt_template.md`;
    if (!(await app.vault.adapter.exists(templatePath))) {
        await app.vault.create(templatePath, 
            "# 思考整理プロンプトテンプレート\n\n" +
            "あなたはユーザーの思考の壁打ち相手であり、卓越した知識を持つAI研究パートナーです。\n" +
            "以下の質問に対して、ただ事実を答えるだけでなく、以下の構成で回答してください。\n\n" +
            "1. **要約**: 質問の核心を一言で整理する\n" +
            "2. **詳細回答**: 科学的・論理的根拠に基づく深い洞察を交えて解説する\n" +
            "3. **さらなる問いの提案**: このテーマを深めるための、次に考えるべき「問い」を2つ提示する\n"
        );
    }
}

// Gemini API 呼び出し (フォールバック機能付き)
async function callGemini(prompt, preferredModel = "gemini-3.5-flash") {
    if (!GEMINI_API_KEY || GEMINI_API_KEY.includes("YOUR_GEMINI_API_KEY")) {
        new Notice("❌ エラー: Gemini APIキーが設定されていません。コード先頭の GEMINI_API_KEY を書き換えてください。");
        throw new Error("APIキー未設定");
    }

    const modelsToTry = [preferredModel];
    if (preferredModel === "gemini-3.5-flash") {
        modelsToTry.push("gemini-3.5-flash-light");
        modelsToTry.push("gemini-3.5-flash-lite");
        modelsToTry.push("gemini-2.0-flash");
    } else {
        modelsToTry.push("gemini-3.5-flash");
        modelsToTry.push("gemini-3.5-flash-light");
        modelsToTry.push("gemini-2.0-flash");
    }

    const uniqueModels = Array.from(new Set(modelsToTry));
    let lastError = null;

    for (const model of uniqueModels) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`;
        try {
            console.log("Trying model in Obsidian:", model);
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    contents: [{
                        parts: [{
                            text: prompt
                        }]
                    }]
                })
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errText}`);
            }

            const data = await response.json();
            console.log("Success with model in Obsidian:", model);
            return {
                text: data.candidates[0].content.parts[0].text,
                model: model
            };
        } catch (e) {
            console.warn(`Model ${model} failed in Obsidian:`, e);
            lastError = e;
        }
    }

    new Notice(`❌ すべてのGeminiモデルの呼び出しに失敗しました: ${lastError.message}`);
    throw lastError;
}

// 【フェーズ1】質問回答処理
async function processQuestions() {
    new Notice("🔄 フェーズ1: 質問処理を開始します...");
    const files = app.vault.getMarkdownFiles().filter(f => f.path.startsWith(QUESTIONS_DIR));
    
    if (files.length === 0) {
        new Notice("01_Questions フォルダにMarkdownファイルが見つかりません。");
        return;
    }

    // テンプレートの取得
    const templatePath = `${TEMPLATES_DIR}/prompt_template.md`;
    let template = "ロジカルかつ多角的な視点から詳細に回答してください。";
    if (await app.vault.adapter.exists(templatePath)) {
        template = await app.vault.adapter.read(templatePath);
    }

    let processedCount = 0;
    for (const file of files) {
        const content = (await app.vault.read(file)).trim();
        if (!content) continue;

        new Notice(`思考中...: ${file.name}`);
        const prompt = `以下のテンプレートに基づいて、質問に対する知的で実用的な回答を生成してください。\n\n【回答テンプレートの構成】\n${template}\n\n【質問内容】\n${content}`;
        
        try {
            const { text: answer, model: usedModel } = await callGemini(prompt);
            const ansPath = `${ANSWERS_DIR}/${file.name}`;
            const ansContent = `# 質問内容\n\n${content}\n\n---\n\n# Geminiからの回答\n\n${answer}\n\n---\n*使用したAIモデル: ${usedModel}*\n`;

            // 保存
            if (await app.vault.adapter.exists(ansPath)) {
                const targetFile = app.vault.getAbstractFileByPath(ansPath);
                await app.vault.modify(targetFile, ansContent);
            } else {
                await app.vault.create(ansPath, ansContent);
            }

            // 元ファイルを空にしてクレンジング
            await app.vault.modify(file, "");
            processedCount++;
            new Notice(`✅ [使用モデル: ${usedModel}] 完了: ${file.name}`);
        } catch (e) {
            new Notice(`❌ 失敗: ${file.name}`);
        }
        // レートリミットウェイト
        await new Promise(r => setTimeout(r, 4000));
    }

    new Notice(`🎉 フェーズ1完了! ${processedCount}件の質問を処理しました。`);
}

// 【フェーズ2】未解決問題のスキャン＆集約
async function poolQuestions() {
    new Notice("🔍 フェーズ2: 全てのノートから未解決の問いをスキャン中...");
    const allFiles = app.vault.getMarkdownFiles().filter(f => !f.path.startsWith(SYSTEM_DIR));
    const questions = new Set();

    for (const file of allFiles) {
        const content = await app.vault.read(file);
        const lines = content.split("\n");
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("?-")) {
                const qText = trimmed.replace(/^\?-\s*/, "").trim();
                if (qText) questions.add(qText);
            }
        }
    }

    if (questions.size === 0) {
        new Notice("?- で始まる未解決の問いは見つかりませんでした。");
        return;
    }

    // 既存ファイルの読み込み
    const unsolvedPath = `${SYSTEM_DIR}/unsolved_questions.md`;
    const existing = new Set();
    if (await app.vault.adapter.exists(unsolvedPath)) {
        const fileContent = await app.vault.adapter.read(unsolvedPath);
        const lines = fileContent.split("\n");
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("- ")) {
                existing.add(trimmed.replace(/^-\s*/, "").trim());
            }
        }
    }

    // マージ
    const merged = new Set([...existing, ...questions]);
    let unsolvedContent = "# 未解決の問いのプール (問いのデータベース)\n\n※ Vault内のノートから自動抽出された未解決の問題です。\n\n";
    for (const q of Array.from(merged).sort()) {
        unsolvedContent += `- ${q}\n`;
    }

    if (await app.vault.adapter.exists(unsolvedPath)) {
        const targetFile = app.vault.getAbstractFileByPath(unsolvedPath);
        await app.vault.modify(targetFile, unsolvedContent);
    } else {
        await app.vault.create(unsolvedPath, unsolvedContent);
    }

    new Notice(`🎉 完了! ${merged.size}件の問いをプールしました。`);
}

// 【フェーズ3】キーワード・メモから新理論生成
async function generateTheories() {
    new Notice("🧪 フェーズ3: キーワードとメモから新理論を構築中...");
    const files = app.vault.getMarkdownFiles().filter(f => f.path.startsWith(BRAINSTORMING_DIR) && !f.name.startsWith("新理論_") && !f.name.startsWith("統合理論_"));
    
    let allKeywords = [];
    let allNotes = [];

    for (const file of files) {
        const content = await app.vault.read(file);
        
        // Front Matterパース
        const fm = app.metadataCache.getFileCache(file)?.frontmatter;
        if (fm && fm.keywords) {
            if (Array.isArray(fm.keywords)) {
                allKeywords.push(...fm.keywords.map(String));
            } else {
                allKeywords.push(String(fm.keywords));
            }
        }

        // メモセクションパース
        const lines = content.split("\n");
        let inSection = false;
        for (const line of lines) {
            const trimmed = line.strip ? line.strip() : line.trim();
            if (trimmed.startsWith("## 印象に残ったメモ")) {
                inSection = true;
                continue;
            } else if (trimmed.startsWith("##") || trimmed.startsWith("#")) {
                inSection = false;
            }

            if (inSection && (trimmed.startsWith("- ") || trimmed.startsWith("* "))) {
                allNotes.push(trimmed.replace(/^[-*]\s*/, "").trim());
            }
        }
    }

    allKeywords = Array.from(new Set(allKeywords));
    allNotes = Array.from(new Set(allNotes));

    if (allKeywords.length === 0 && allNotes.length === 0) {
        new Notice("パース可能なキーワード、または印象に残ったメモが見つかりません。");
        return;
    }

    new Notice(`キーワード ${allKeywords.length}件, メモ ${allNotes.length}件 をもとに新理論を生成します...`);
    const kwsStr = allKeywords.slice(0, 5).map(k => `- ${k}`).join("\n");
    const notesStr = allNotes.slice(0, 3).map(n => `- ${n}`).join("\n");

    const prompt = `あなたは、異なる分野のアイデアや概念を組み合わせ、画期的でアヴァンギャルドな新しい科学的・哲学的理論を提唱する天才研究者です。\n\n以下のデータをもとに、これらを高次元で結合した「新しい理論」を作成してください。\n\n【インプットデータ】\n${allKeywords.length ? "■ キーワード:\n" + kwsStr : ""}\n${allNotes.length ? "■ 印象に残ったメモ:\n" + notesStr : ""}\n\n【理論生成ルール】\n1. 理論に魅力的でキャッチーな「理論名（タイトル）」を付与してください。\n2. 理論の核心となるコンセプトを、一般人でもワクワクするが、専門的にも緻密なロジックで説明してください。\n3. この理論に関連する「実在の科学的キーワード、先行研究の検索クエリ候補」を5つ挙げてください。\n4. この理論に対する「想定される学術的・技術的な批判、反論、または限界」をセットで3つ出力してください。\n\n理論は、Markdown形式で美しく整形して出力してください。`;

    try {
        const { text: theory, model: usedModel } = await callGemini(prompt);
        const timestamp = moment().format("YYYYMMDD_HHmmss");
        const theoryPath = `${BRAINSTORMING_DIR}/新理論_${timestamp}.md`;
        const theoryWithModel = theory + `\n\n---\n*使用したAIモデル: ${usedModel}*`;

        await app.vault.create(theoryPath, theoryWithModel);
        new Notice(`🎉 [使用モデル: ${usedModel}] 新理論が創出されました！: ${theoryPath}`);
    } catch (e) {
        new Notice(`❌ 新理論の生成に失敗しました: ${e.message}`);
    }
}

// 【フェーズ4】arXiv 検索
async function runArxiv() {
    new Notice("📚 フェーズ4: arXivでの学術調査を開始します...");
    let query = "Self-organization";

    const unsolvedPath = `${SYSTEM_DIR}/unsolved_questions.md`;
    if (await app.vault.adapter.exists(unsolvedPath)) {
        const content = await app.vault.adapter.read(unsolvedPath);
        const questions = content.split("\n")
            .filter(line => line.trim().startsWith("- "))
            .map(line => line.replace(/^-\s*/, "").trim());
        
        if (questions.length > 0) {
            query = questions[Math.floor(Math.random() * questions.length)];
        }
    }

    new Notice(`クエリ: 「${query}」について論文検索中...`);
    const encodedQuery = encodeURIComponent(query);
    const arxivUrl = `https://export.arxiv.org/api/query?search_query=all:${encodedQuery}&max_results=2`;

    try {
        const res = await fetch(arxivUrl);
        const text = await res.text();
        
        // 簡易 XML パース (タイトルとアブストラクトの抽出)
        const entries = text.split("<entry>");
        if (entries.length <= 1) {
            new Notice("論文が見つかりませんでした。");
            return;
        }

        const papers = [];
        for (let i = 1; i < Math.min(entries.length, 3); i++) {
            const entry = entries[i];
            const titleMatch = entry.match(/<title>([\s\S]*?)<\/title>/);
            const summaryMatch = entry.match(/<summary>([\s\S]*?)<\/summary>/);
            const idMatch = entry.match(/<id>([\s\S]*?)<\/id>/);
            
            const title = titleMatch ? titleMatch[1].replace(/\n/g, " ").trim() : "Unknown Title";
            const abstract = summaryMatch ? summaryMatch[1].replace(/\n/g, " ").trim() : "No abstract available";
            const pdfUrl = idMatch ? idMatch[1].trim() : "";

            papers.push({ title, abstract, pdfUrl });
        }

        let arxivReport = `# arXiv 学術検索サマリー\n\n**調査クエリ**: ${query}\n\n---\n\n`;

        for (let i = 0; i < papers.length; i++) {
            const paper = papers[i];
            new Notice(`論文 ${i+1} の要約をGeminiで生成中...`);

            const prompt = `以下の学術論文の英語タイトルとアブストラクトを読み込み、日本語で「3行要約」と「貢献度スコアリング(A〜C)」を作成してください。\n\n【論文情報】\nタイトル: ${paper.title}\nアブストラクト: ${paper.abstract}\n\n【出力ルール】\n1. **3行要約**:\n   - 1行目: 課題の記述\n   - 2行目: アプローチの記述\n   - 3行目: インパクトや可能性の記述\n2. **貢献度スコア**:\n   - A（極めて革新しい）、B（興味深い）、C（限定的）から選択。\n\n日本語でロジカルに出力してください。`;

            const { text: evaluation, model: usedModel } = await callGemini(prompt);
            arxivReport += `## ${i+1}. ${paper.title}\n- **リンク**: ${paper.pdfUrl}\n\n### Gemini 評価 & 3行サマリー (使用モデル: ${usedModel})\n\n${evaluation}\n\n---\n\n`;
            
            await new Promise(r => setTimeout(r, 4000)); // RPM制限
        }

        const summaryPath = `${SYSTEM_DIR}/arxiv_summary.md`;
        if (await app.vault.adapter.exists(summaryPath)) {
            const existingContent = await app.vault.adapter.read(summaryPath);
            await app.vault.modify(app.vault.getAbstractFileByPath(summaryPath), existingContent + "\n\n" + arxivReport);
        } else {
            await app.vault.create(summaryPath, arxivReport);
        }

        new Notice("🎉 arXiv調査完了! 99_System/arxiv_summary.md に保存しました。");
    } catch (e) {
        new Notice(`❌ arXiv調査失敗: ${e.message}`);
    }
}

// 【フェーズ5】2理論の構造的統合 (新機能)
async function integrateTheoriesInteractive() {
    new Notice("🌌 2理論の構造的統合フェーズを起動します");

    const theoryA = await tp.system.prompt("理論A（または概念・キーワード）を入力してください:");
    if (!theoryA) return;

    const theoryB = await tp.system.prompt("理論B（または概念・キーワード）を入力してください:");
    if (!theoryB) return;

    const approachChoice = await tp.system.suggester(
        ["1. 構造的同型性発見型 (論理的アナロジーによる写像)", 
         "2. 視点・レンズ適用型 (理論Aの視座から理論Bを記述)", 
         "3. 弁証法（矛盾解消）型 (対立命題をアウフヘーベン)", 
         "4. アノマリーブレイクスルー型 (例外から新公理を導出)", 
         "5. 自動最適化 (Geminiが最適な統合パスを決定)"],
        ["1. 構造的同型性発見型", "2. 視点・レンズ適用型", "3. 弁証法（矛盾解消）型", "4. アノマリーブレイクスルー型", "5. 自動最適化"]
    );
    if (!approachChoice) return;

    new Notice("💡 Geminiが世界最高峰の科学哲学者として構造的思考を実行中...");

    const prompt = `あなたは異分野の概念を融合させ、新たなパラダイムを創出することに長けた、世界最高峰の科学哲学者であり理論モデラーです。
提示された2つの異なる理論（または概念・メモ）の根底にある抽象的な構造を見抜き、それらを論理的・数理的に統合した「新しい思考フレームワーク（新理論）」を構築することがあなたの任務です。

評価の甘い安易な結合ではなく、両者の「前提の衝突」や「限界点」を厳しく批判的に検証した上で、それらを高次元で解消（アウフヘーベン）する、学術的に堅牢なプロトタイプ（仮説）を提示してください。

【出力時の絶対ルール】
1. 指定された思考ステップ（Step 1 〜 Step 5）を絶対に省略せず、段階的に思考を展開すること。
2. 専門用語（例: 構造的同型性、写像、エントロピー等）は文脈に即して厳密に使用すること。
3. 最後に、理論の堅牢性を担保するため、以下の「検証・批判セクション」を自動的に付加すること。
   - 「この理論に関連する実在の科学的キーワード、先行研究の検索クエリ候補」を5つ挙げる。
   - 「この理論に対する想定される批判・反論」や「技術的な限界」をセットで3つ挙げる。

# 入力情報
- 【理論A】：${theoryA}
- 【理論B】：${theoryB}

# 適用する統合アプローチ（以下の【 】から1つを選択、または「自動最適化」と指定してください）
【選択肢：1. 構造的同型性発見型 / 2. 視点・レンズ適用型 / 3. 弁証法（矛盾解消）型 / 4. アノマリーブレイクスルー型 / 5. 自動最適化】
アプローチ：${approachChoice}

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
※この理論が直面するであろう論理的破綻の可能性や、実証における限界。`;

    try {
        const { text: result, model: usedModel } = await callGemini(prompt, "gemini-3.5-flash"); // 思考用最新モデル
        const timestamp = moment().format("YYYYMMDD_HHmmss");
        const integratedPath = `${BRAINSTORMING_DIR}/統合理論_${timestamp}.md`;
        const resultWithModel = result + `\n\n---\n*使用したAIモデル: ${usedModel}*`;

        await app.vault.create(integratedPath, resultWithModel);
        new Notice(`🎉 [使用モデル: ${usedModel}] 新たな学術フレームワークが創出されました！: ${integratedPath}`);
    } catch (e) {
        new Notice(`❌ 構造的統合に失敗しました: ${e.message}`);
    }
}

// ============================================
// メインメニューの表示
// ============================================
await initStructure();

const phaseChoice = await tp.system.suggester(
    ["1: 【F1】質問回答の自動処理 & クレンジング", 
     "2: 【F2】未解決問題の自動プールスキャン", 
     "3: 【F3】キーワード・日常メモから新理論自動生成", 
     "4: 【F4】arXiv論文の自動検索・要約・評価", 
     "5: 【F5】2つの異なる理論の構造的統合 (新機能)",
     "❌ キャンセル"],
    ["1", "2", "3", "4", "5", "cancel"]
);

if (phaseChoice === "1") {
    await processQuestions();
} else if (phaseChoice === "2") {
    await poolQuestions();
} else if (phaseChoice === "3") {
    await generateTheories();
} else if (phaseChoice === "4") {
    await runArxiv();
} else if (phaseChoice === "5") {
    await integrateTheoriesInteractive();
} else {
    new Notice("処理はキャンセルされました。");
}
%>