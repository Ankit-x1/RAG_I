import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Set

from qdrant_client import QdrantClient, models

from backend.indexing.crawler import crawl_fastapi_docs
from backend.indexing.chunker import semantic_chunk
from backend.indexing.embedder import EmbeddingGenerator

logger = logging.getLogger(__name__)

# Constants for Qdrant
COLLECTION_NAME = "fastapi_docs"
VECTOR_SIZE = 384  # Matches 'sentence-transformers/all-MiniLM-L6-v2' output dimension
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333)) # Default gRPC port

# Constants for pipeline
CHECKPOINT_FILE = "data/processed/last_indexed.json"
UPLOAD_BATCH_SIZE = 100

async def run_indexing():
    """
    Executes the full indexing pipeline: crawls, chunks, embeds, and uploads to Qdrant.
    Includes checkpointing for resuming.
    """
    logger.info("Starting indexing pipeline...")

    # 1. Initialize Qdrant Client
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    embedder = EmbeddingGenerator()

    # 2. Check and create Qdrant collection
    try:
        if not client.collection_exists(collection_name=COLLECTION_NAME):
            logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}'...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
            )
            logger.info(f"Collection '{COLLECTION_NAME}' created.")
        else:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant or create collection: {e}")
        return

    # 3. Load checkpoint
    indexed_urls: Set[str] = set()
    last_run_timestamp = None
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                checkpoint_data = json.load(f)
                indexed_urls = set(checkpoint_data.get("indexed_urls", []))
                last_run_timestamp = checkpoint_data.get("last_run_timestamp")
            logger.info(f"Checkpoint loaded. {len(indexed_urls)} URLs previously indexed.")
            if last_run_timestamp:
                logger.info(f"Last successful run: {last_run_timestamp}")
        except json.JSONDecodeError:
            logger.warning("Invalid checkpoint file, starting fresh indexing.")
            indexed_urls = set()
            last_run_timestamp = None
    else:
        logger.info("No checkpoint file found, starting fresh indexing.")

    # 4. Crawl documents
    all_crawled_docs = await crawl_fastapi_docs()
    logger.info(f"Finished crawling. Found {len(all_crawled_docs)} documents.")

    # Filter out already indexed documents
    new_docs_to_index = [
        doc for doc in all_crawled_docs if doc["url"] not in indexed_urls
    ]
    logger.info(f"Found {len(new_docs_to_index)} new documents to index.")

    if not new_docs_to_index:
        logger.info("No new documents to index. Exiting.")
        return

    # 5. Chunk, Embed, and Upload
    all_chunks: List[Dict] = []
    for doc in new_docs_to_index:
        try:
            chunks = semantic_chunk(doc)
            all_chunks.extend(chunks)
            indexed_urls.add(doc["url"]) # Add to set as soon as processed for chunking
        except Exception as e:
            logger.error(f"Error chunking document {doc['url']}: {e}")
            # Optionally, we might not add this URL to indexed_urls if chunking failed
            # But for simplicity, we assume if crawling was successful, we tried to chunk.

    logger.info(f"Total {len(all_chunks)} chunks generated.")

    # Prepare for batch embedding and upload
    current_texts_batch: List[str] = []
    current_payloads_batch: List[Dict] = []
    points_to_upload: List[models.PointStruct] = []

    for i, chunk in enumerate(all_chunks):
        current_texts_batch.append(chunk["text"])
        current_payloads_batch.append(chunk["metadata"])

        if len(current_texts_batch) >= UPLOAD_BATCH_SIZE or i == len(all_chunks) - 1:
            try:
                embeddings = embedder.embed_batch(current_texts_batch)
                
                for j, emb in enumerate(embeddings):
                    points_to_upload.append(
                        models.PointStruct(
                            vector=emb.tolist(),
                            payload=current_payloads_batch[j],
                        )
                    )
                
                # Upload to Qdrant in batches
                if points_to_upload:
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=points_to_upload,
                        wait=True,
                    )
                    logger.info(f"Uploaded {len(points_to_upload)} points to Qdrant.")
                
            except Exception as e:
                logger.error(f"Error embedding or uploading a batch of chunks: {e}")
            finally:
                current_texts_batch = []
                current_payloads_batch = []
                points_to_upload = []


    # 6. Save checkpoint
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({
                "indexed_urls": list(indexed_urls),
                "last_run_timestamp": datetime.now().isoformat()
            }, f, indent=2)
        logger.info(f"Checkpoint saved to {CHECKPOINT_FILE}.")
    except Exception as e:
        logger.error(f"Failed to save checkpoint file: {e}")

    logger.info("Indexing pipeline finished.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Run pipeline
    asyncio.run(run_indexing())

    # To run this, you need a Qdrant instance running, e.g., via Docker:
    # docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
