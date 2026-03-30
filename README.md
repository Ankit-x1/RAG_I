# Retrieval Augmented Generation (RAG) Project

This project implements a Retrieval Augmented Generation (RAG) system to enhance AI responses by grounding them in a knowledge base of relevant documents. The system aims to provide more accurate, current, and contextually rich answers by retrieving information from various sources (web pages, PDFs, etc.) and feeding it to a large language model (LLM). The goal is to overcome the limitations of LLMs' static training data, hallucination tendencies, and lack of real-time information access, thereby improving the reliability and trustworthiness of AI-generated content.

## Setup Instructions

1.  **Start Qdrant Vector Database**:
    ```bash
    docker-compose up -d qdrant
    ```

2.  **Install Poetry (if you don't have it)**:
    ```bash
    pip install poetry
    ```

3.  **Install Python Dependencies**:
    ```bash
    poetry install
    ```

4.  **Create `.env` file**:
    Copy `.env.example` to `.env` and fill in your API keys and configuration.
    ```bash
    cp .env.example .env
    ```

## How to Run the Backend API

To start the FastAPI backend server:

```bash
poetry run uvicorn backend.api.main:app --reload
```

## Architecture Diagram

```
+------------------+     +-----------------------+     +-----------------+
|   User/Client    |<--->|      FastAPI App      |<--->|   LLM (Groq)    |
|                  |     |  (backend.api.main)   |     |                 |
+------------------+     +----------^------------+     +-----------------+
                                    |
                                    v
+------------------+     +-----------------------+     +-----------------+
| Web Scrapers/    |---->|   Document Loader     |---->| Text Splitter   |
| PDF Parsers      |     | (beautifulsoup4, httpx)|     | (tiktoken)      |
+------------------+     +-----------------------+     +-----------------+
                                    |
                                    v
+------------------+     +-----------------------+     +-----------------+
|  Embedding Model |<----|   Vectorizer          |---->| Qdrant Vector   |
| (sentence-        |     | (sentence-transformers)|     | Database        |
| transformers)    |     +-----------------------+     +-----------------+
                                    ^
                                    |
+------------------+                |
| BM25 Ranker      |----------------+
| (rank-bm25)      |
+------------------+
```
