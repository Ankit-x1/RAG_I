import re
from typing import Dict, Iterable, List


MAX_CHUNK_TOKENS = 400
OVERLAP_TOKENS = 50
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


def _count_tokens(text: str) -> int:
    """Use a simple whitespace token count for chunk sizing."""
    return len(text.split())


def _split_sentences(text: str) -> List[str]:
    """
    Split text into rough sentence units without requiring external tokenizer data.

    Code fences are preserved as single units because they should not be broken apart.
    """
    parts = re.split(r"(```[\s\S]*?```)", text)
    sentences: List[str] = []

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if stripped.startswith("```") and stripped.endswith("```"):
            sentences.append(stripped)
            continue

        fragments = SENTENCE_BOUNDARY_RE.split(stripped)
        sentences.extend(fragment.strip() for fragment in fragments if fragment.strip())

    return sentences


def _iter_sections(doc: Dict) -> Iterable[Dict[str, str]]:
    sections = doc.get("sections")
    if sections:
        for section in sections:
            heading = section.get("heading") or doc["title"]
            content = section.get("content", "").strip()
            if content:
                yield {"heading": heading, "content": content}
        return

    content = doc.get("content", "").strip()
    if content:
        yield {"heading": doc["title"], "content": content}


def semantic_chunk(doc: Dict) -> List[Dict]:
    """
    Split a document into overlapping chunks while preserving section metadata.
    """
    chunks: List[Dict] = []

    for section in _iter_sections(doc):
        _chunk_text_by_sentences(
            text=section["content"],
            url=doc["url"],
            doc_title=doc["title"],
            section_title=section["heading"],
            chunks=chunks,
        )

    return chunks


def _chunk_text_by_sentences(
    text: str,
    url: str,
    doc_title: str,
    section_title: str,
    chunks: List[Dict],
) -> None:
    sentences = _split_sentences(text)
    if not sentences:
        return

    current_chunk_sentences: List[str] = []
    current_chunk_tokens = 0

    for sentence in sentences:
        sentence_tokens = _count_tokens(sentence)

        if current_chunk_sentences and current_chunk_tokens + sentence_tokens > MAX_CHUNK_TOKENS:
            chunks.append(
                {
                    "text": " ".join(current_chunk_sentences).strip(),
                    "metadata": {
                        "url": url,
                        "title": doc_title,
                        "section": section_title,
                    },
                }
            )

            overlap_sentences: List[str] = []
            overlap_token_count = 0
            for overlap_sentence in reversed(current_chunk_sentences):
                overlap_sentence_tokens = _count_tokens(overlap_sentence)
                if overlap_token_count + overlap_sentence_tokens > OVERLAP_TOKENS:
                    break
                overlap_sentences.insert(0, overlap_sentence)
                overlap_token_count += overlap_sentence_tokens

            current_chunk_sentences = overlap_sentences
            current_chunk_tokens = _count_tokens(" ".join(current_chunk_sentences))

        if sentence_tokens > MAX_CHUNK_TOKENS:
            if current_chunk_sentences:
                chunks.append(
                    {
                        "text": " ".join(current_chunk_sentences).strip(),
                        "metadata": {
                            "url": url,
                            "title": doc_title,
                            "section": section_title,
                        },
                    }
                )
                current_chunk_sentences = []
                current_chunk_tokens = 0

            chunks.append(
                {
                    "text": sentence.strip(),
                    "metadata": {
                        "url": url,
                        "title": doc_title,
                        "section": section_title,
                    },
                }
            )
            continue

        current_chunk_sentences.append(sentence)
        current_chunk_tokens += sentence_tokens

    if current_chunk_sentences:
        chunks.append(
            {
                "text": " ".join(current_chunk_sentences).strip(),
                "metadata": {
                    "url": url,
                    "title": doc_title,
                    "section": section_title,
                },
            }
        )
