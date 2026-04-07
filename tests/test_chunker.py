from backend.indexing.chunker import semantic_chunk


def test_semantic_chunk_preserves_section_metadata() -> None:
    doc = {
        "url": "https://example.com/docs",
        "title": "Example Docs",
        "content": "ignored when sections are present",
        "sections": [
            {
                "heading": "Getting Started",
                "content": "Install the package. Configure the service. Run the app.",
            },
            {
                "heading": "Reference",
                "content": "```python\nprint('hello')\n```\nReturn the status code.",
            },
        ],
    }

    chunks = semantic_chunk(doc)

    assert len(chunks) == 2
    assert chunks[0]["metadata"]["section"] == "Getting Started"
    assert "Install the package." in chunks[0]["text"]
    assert chunks[1]["metadata"]["section"] == "Reference"
    assert "```python" in chunks[1]["text"]


def test_semantic_chunk_splits_large_section_with_overlap() -> None:
    long_sentence = " ".join(["token"] * 45) + "."
    doc = {
        "url": "https://example.com/large",
        "title": "Large Doc",
        "content": "",
        "sections": [
            {
                "heading": "Large Section",
                "content": " ".join([long_sentence] * 12),
            }
        ],
    }

    chunks = semantic_chunk(doc)

    assert len(chunks) > 1
    assert chunks[0]["metadata"]["section"] == "Large Section"
    assert chunks[0]["text"].split()[-45:] == chunks[1]["text"].split()[:45]
