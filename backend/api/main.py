from fastapi import BackgroundTasks, FastAPI, Query, HTTPException
from pydantic import BaseModel
import logging

from backend.models.agent import RAGAgent, QueryResult
from backend.models.config import RAGConfig

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Backend",
    version="0.2.0",
    description="Retrieval-Augmented Generation API with vector search and LLM integration.",
)

# Initialize RAG agent at startup
rag_agent: RAGAgent = None


@app.on_event("startup")
async def startup_event():
    """Initialize RAG agent on startup."""
    global rag_agent
    try:
        config = RAGConfig.from_env()
        rag_agent = RAGAgent(config)
        logger.info("RAG Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG Agent: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down RAG Backend")


# === Request/Response Models ===

class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    query: str
    top_k: int = 5
    use_history: bool = True


class QueryResponse(BaseModel):
    """Response model for RAG queries."""
    query: str
    response: str
    sources: list[dict]
    metadata: dict


class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str
    system_prompt: str = None


class StatusResponse(BaseModel):
    """Response model for agent status."""
    status: str
    queries_processed: int
    collection: dict
    conversation_turns: int


# === Health & Status Endpoints ===

@app.get("/health")
async def healthcheck() -> dict[str, str]:
    """Check if the service is running."""
    return {"status": "ok"}


@app.get("/status")
async def get_status() -> StatusResponse:
    """Get RAG agent status and statistics."""
    if rag_agent is None:
        raise HTTPException(status_code=500, detail="RAG Agent not initialized")
    
    status = rag_agent.get_status()
    return StatusResponse(**status)


# === Indexing Endpoints ===

@app.post("/index")
async def trigger_indexing(
    background_tasks: BackgroundTasks,
    wait: bool = Query(
        default=False,
        description="Run indexing inline instead of in the background.",
    ),
) -> dict[str, str]:
    """
    Trigger the indexing pipeline to crawl, chunk, embed, and index documents.
    """
    from backend.indexing.pipeline import run_indexing

    if wait:
        await run_indexing()
        return {"status": "completed"}

    background_tasks.add_task(run_indexing)
    return {"status": "scheduled"}


# === RAG Query Endpoints ===

@app.post("/query")
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a query using RAG (Retrieval-Augmented Generation).
    
    Returns:
    - The generated response
    - Retrieved source documents
    - Metadata about the query
    """
    if rag_agent is None:
        raise HTTPException(status_code=500, detail="RAG Agent not initialized")
    
    try:
        result: QueryResult = rag_agent.query(
            request.query,
            top_k=request.top_k,
            use_history=request.use_history,
        )
        
        return QueryResponse(
            query=result.query,
            response=result.response,
            sources=result.retrieved_chunks,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/batch-query")
async def batch_query(queries: list[str]) -> list[QueryResponse]:
    """
    Process multiple queries in batch.
    """
    if rag_agent is None:
        raise HTTPException(status_code=500, detail="RAG Agent not initialized")
    
    try:
        results = rag_agent.batch_query(queries)
        return [
            QueryResponse(
                query=r.query,
                response=r.response,
                sources=r.retrieved_chunks,
                metadata=r.metadata,
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error in batch query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing queries: {str(e)}")


@app.post("/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    """
    Have a multi-turn conversation with the RAG agent.
    Context is maintained across turns.
    """
    if rag_agent is None:
        raise HTTPException(status_code=500, detail="RAG Agent not initialized")
    
    try:
        response = rag_agent.chat(
            request.message,
            system_prompt=request.system_prompt,
        )
        return {
            "message": request.message,
            "response": response,
        }
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")


@app.post("/clear-history")
async def clear_conversation_history() -> dict[str, str]:
    """Clear the conversation history."""
    if rag_agent is None:
        raise HTTPException(status_code=500, detail="RAG Agent not initialized")
    
    rag_agent.clear_history()
    return {"status": "history cleared"}
