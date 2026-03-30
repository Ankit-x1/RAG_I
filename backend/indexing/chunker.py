import re
from typing import Dict, List
import nltk

# NLTK's Punkt tokenizer is good for sentence splitting
# Make sure to run: python -c "import nltk; nltk.download('punkt', quiet=True)"

def _count_tokens(text: str) -> int:
    """Simple token count by splitting on whitespace."""
    return len(text.split())

def semantic_chunk(doc: Dict) -> List[Dict]:
    """
    Splits a document into semantic chunks based on headers and sentence boundaries,
    with overlap. Code blocks are treated as part of the text.

    Args:
        doc: A dictionary containing 'url', 'title', 'content', and 'code_blocks'.
             'content' is expected to include code blocks in markdown format (```python...```).

    Returns:
        A list of dictionaries, where each dictionary represents a chunk
        with 'text' and 'metadata'.
    """
    url = doc["url"]
    title = doc["title"]
    content = doc["content"]
    
    chunks: List[Dict] = []
    
    # Split content by H2 tags first
    # Using regex to find <h2> patterns. We assume H2 tags were converted to text like "\n\nHeader Text\n\n"
    # or similar markers. Let's use a simpler approach based on the content string
    # where H2s might appear as distinct lines of text or sections.
    # The crawler now puts headers back in, so we can split on string patterns that look like headers.
    
    # Heuristic: split by lines that seem like H2s. This is a simplification.
    # A more robust solution would involve explicit HTML tags or structured content from the crawler.
    # For now, let's look for large bolded lines as potential section headers.
    # Given the markdown-like content, actual <h2> tags are not present,
    # but the text content for H2s will be distinct.
    
    # For simplicity, let's treat the content as one large text block initially,
    # and then apply sentence splitting and token limits.
    # If the intent was to *really* split on HTML <h2> tags, the crawler would need
    # to pass that structure more explicitly or convert them to a unique, reliable marker.
    
    # Let's use the actual text of H2s if they were identified in the crawler content.
    # The crawler now injects H2 text like "\n\nHeader Text\n\n".
    
    # Split the main content into sections based on potential H2-like patterns
    # This regex looks for two or more newline characters followed by non-newline characters and then two or more newline characters,
    # capturing the header text in between. This is a heuristic.
    sections_raw = re.split(r'(\n\n[^\n]+?\n\n)', content)
    
    current_section_title = title # Default section title for content before the first H2
    current_section_content_parts: List[str] = []

    for part in sections_raw:
        if re.fullmatch(r'\n\n[^\n]+?\n\n', part): # This is a potential H2 section delimiter
            header_text = part.strip()
            
            # Process accumulated content for the previous section
            if current_section_content_parts:
                section_text = " ".join(current_section_content_parts).strip()
                if section_text:
                    _chunk_text_by_sentences(section_text, url, title, current_section_title, chunks)
            
            current_section_title = header_text # Update section title
            current_section_content_parts = [] # Reset for new section
        elif part.strip(): # Regular content part
            current_section_content_parts.append(part.strip())

    # Process any remaining content for the last section
    if current_section_content_parts:
        section_text = " ".join(current_section_content_parts).strip()
        if section_text:
            _chunk_text_by_sentences(section_text, url, title, current_section_title, chunks)

    return chunks

def _chunk_text_by_sentences(text: str, url: str, doc_title: str, section_title: str, chunks: List[Dict]):
    """
    Helper to chunk a given text block by sentences with overlap.
    """
    sentences = nltk.sent_tokenize(text)
    current_chunk_sentences: List[str] = []
    current_chunk_tokens = 0
    overlap_tokens = 50
    max_chunk_tokens = 400

    for i, sentence in enumerate(sentences):
        sentence_tokens = _count_tokens(sentence)

        if current_chunk_tokens + sentence_tokens <= max_chunk_tokens:
            current_chunk_sentences.append(sentence)
            current_chunk_tokens += sentence_tokens
        else:
            if current_chunk_sentences:
                chunks.append({
                    "text": " ".join(current_chunk_sentences).strip(),
                    "metadata": {"url": url, "title": doc_title, "section": section_title}
                })

            # Start new chunk with overlap
            current_chunk_sentences = []
            overlap_buffer_sentences = []
            
            # Add sentences from the end of the previous chunk to create overlap
            temp_tokens = 0
            for j in range(len(sentences[:i]) -1, -1, -1):
                overlap_sentence = sentences[j]
                if temp_tokens + _count_tokens(overlap_sentence) <= overlap_tokens:
                    overlap_buffer_sentences.insert(0, overlap_sentence)
                    temp_tokens += _count_tokens(overlap_sentence)
                else:
                    break
            
            current_chunk_sentences.extend(overlap_buffer_sentences)
            current_chunk_sentences.append(sentence)
            current_chunk_tokens = _count_tokens(" ".join(current_chunk_sentences))


    # Add the last chunk if it's not empty
    if current_chunk_sentences:
        chunks.append({
            "text": " ".join(current_chunk_sentences).strip(),
            "metadata": {"url": url, "title": doc_title, "section": section_title}
        })


if __name__ == "__main__":
    test_doc = {
        "url": "https://fastapi.tiangolo.com/tutorial/first-steps/",
        "title": "First Steps - FastAPI",
        "content": (
            "This is an introductory paragraph. It talks about FastAPI. "
            "It's really cool and easy to use. "
            "\n\nFirst Section Header\n\n"
            "Here's some content for the first section. It describes how to set up. "
            "You just need to install a few things. "
            "```python\nfrom fastapi import FastAPI\napp = FastAPI()\n```\n"
            "More text after the code block. This is still part of the first section. "
            "The section continues for a while, making sure it has more than 400 tokens." * 50
            "\n\nSecond Section Header\n\n"
            "This is the second section. It explains advanced features. "
            "This part is also quite long, to test sentence splitting. " * 40
            "```python\n@app.get(\"/\")\nasync def read_root():\n    return {\"Hello\": \"World\"}\n```\n"
            "Final paragraph of the document."
        ),
        "code_blocks": [
            "from fastapi import FastAPI\napp = FastAPI()",
            "@app.get(\"/\")\nasync def read_root():\n    return {\"Hello\": \"World\"}",
        ],
    }

    chunks = semantic_chunk(test_doc)
    print(f"Generated {len(chunks)} chunks.")
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i+1} (Section: {chunk['metadata']['section']}) ---")
        print(f"Tokens: {_count_tokens(chunk['text'])}")
        print(chunk["text"][:200], "...")
        print("-" * 20)
