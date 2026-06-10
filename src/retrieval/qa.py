from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return metadata["authors_joined"]
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return metadata["published"]
    if "what categories" in lowered:
        return metadata["categories_joined"]
    return first_sentence(metadata["summary"])


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add src directory to PYTHONPATH automatically if running directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    from core.config import load_settings
    from retrieval.index import LocalEmbeddingIndex
    
    print("Loading settings...")
    settings = load_settings()
    
    print("Loading Local Embedding Index...")
    try:
        index = LocalEmbeddingIndex.load(settings)
        print("Index loaded successfully.")
    except Exception as e:
        print(f"Error loading index: {e}. Build the index first by running index.py.", file=sys.stderr)
        sys.exit(1)
        
    questions = [
        "Who authored the paper titled 'Operationalizing Reliability Gaps in Large Language Models: A Semi-Systematic Evidence Map of Reasoning, Factuality, Evaluation, and Retrieval-Augmented Generation'?",
        "When was the paper titled 'Operationalizing Reliability Gaps in Large Language Models: A Semi-Systematic Evidence Map of Reasoning, Factuality, Evaluation, and Retrieval-Augmented Generation' published?",
        "Summarize the main topics of retrieval augmented generation reliability."
    ]
    
    for q in questions:
        print(f"\nQuestion: {q}")
        res = answer_question(q, settings, index)
        print(f"Answer: {res.answer}")
        print(f"Retrieved Doc ID: {res.retrieved_doc_ids[0] if res.retrieved_doc_ids else 'None'}")
