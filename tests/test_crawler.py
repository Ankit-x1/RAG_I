from backend.indexing.crawler import _normalize_url, _parse_page


def test_parse_page_returns_sections_and_code_blocks() -> None:
    html = """
    <html>
      <head><title>FastAPI Docs</title></head>
      <body>
        <article class="md-content__inner">
          <h1>Intro</h1>
          <p>Welcome to the guide.</p>
          <h2>Install</h2>
          <p>Install dependencies.</p>
          <pre>pip install fastapi</pre>
        </article>
      </body>
    </html>
    """

    parsed = _parse_page(html, "https://fastapi.tiangolo.com/tutorial/")

    assert parsed["title"] == "FastAPI Docs"
    assert parsed["code_blocks"] == ["pip install fastapi"]
    assert parsed["sections"] == [
        {"heading": "Intro", "content": "Welcome to the guide."},
        {
            "heading": "Install",
            "content": "Install dependencies.\n```python\npip install fastapi\n```",
        },
    ]


def test_normalize_url_strips_query_fragment_and_trailing_slash() -> None:
    normalized = _normalize_url("https://fastapi.tiangolo.com/tutorial/?x=1#part")
    assert normalized == "https://fastapi.tiangolo.com/tutorial"
