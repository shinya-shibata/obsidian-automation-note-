import arxiv
from typing import List, Dict, Any

def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    arXiv APIを使用して検索クエリにマッチする論文を検索し、情報を取得する (機能4)
    """
    print(f"arXivで検索中: '{query}'...")
    results_list = []
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        for result in search.results():
            results_list.append({
                "title": result.title,
                "authors": ", ".join([author.name for author in result.authors]),
                "published": result.published.strftime("%Y"),
                "pdf_url": result.pdf_url,
                "abstract": result.summary
            })
    except Exception as e:
        print(f"arXiv 検索エラー: {e}")
    return results_list
