# Retrieval Augmented Generation (RAG) Project

This project implements the ingestion side of a Retrieval Augmented Generation (RAG) system. It crawls FastAPI documentation, chunks the extracted content, generates embeddings, and stores those vectors in Qdrant so an application layer can retrieve grounded context later.

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

Available endpoints:

- `GET /health` returns a basic health response.
- `POST /index` schedules the indexing pipeline in the background.
- `POST /index?wait=true` runs the indexing pipeline inline and waits for completion.

To run the indexing pipeline directly without the API:

```bash
poetry run python -m backend.indexing.pipeline
```

## Architecture Diagram

```
+------------------+     +-----------------------+
|   User/Client    |<--->|      FastAPI App      |
|                  |     |  (backend.api.main)   |
+------------------+     +----------^------------+
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
```
