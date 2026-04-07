"""
Tests for RAG models and components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.models.config import RAGConfig, QdrantConfig, EmbeddingConfig, GroqConfig


def test_qdrant_config_from_env():
    """Test Qdrant configuration initialization."""
    config = QdrantConfig()
    assert config.host == "localhost"
    assert config.port == 6333
    assert config.vector_size == 384


def test_embedding_config_from_env():
    """Test embedding configuration initialization."""
    config = EmbeddingConfig()
    assert "sentence-transformers" in config.model_name
    assert config.batch_size == 32


def test_groq_config_from_env():
    """Test Groq configuration initialization."""
    config = GroqConfig()
    # Note: API key will be empty if not set in env
    assert config.model == "mixtral-8x7b-32768"
    assert config.temperature == 0.7


def test_rag_config_from_env():
    """Test comprehensive RAG configuration."""
    config = RAGConfig.from_env()
    
    assert config.qdrant.collection_name == "fastapi_docs"
    assert config.embedding.batch_size == 32
    assert config.top_k_retrieval == 5
    assert config.similarity_threshold == 0.5


@patch("backend.models.retriever.QdrantClient")
@patch("backend.models.retriever.EmbeddingGenerator")
def test_retriever_initialization(mock_embedder, mock_qdrant):
    """Test Retriever initialization."""
    from backend.models.retriever import Retriever
    
    config = RAGConfig.from_env()
    retriever = Retriever(config)
    
    assert retriever.config == config
    assert retriever.collection_name == "fastapi_docs"
    mock_qdrant.assert_called_once()


@patch("backend.models.retriever.QdrantClient")
@patch("backend.models.retriever.EmbeddingGenerator")
def test_retriever_retrieve(mock_embedder, mock_qdrant):
    """Test retriever.retrieve method."""
    from backend.models.retriever import Retriever
    
    config = RAGConfig.from_env()
    
    # Mock embedder
    mock_embedder_instance = MagicMock()
    mock_embedder.return_value = mock_embedder_instance
    mock_embedder_instance.embed_batch.return_value = [[0.1, 0.2, 0.3]]
    
    # Mock Qdrant search results
    mock_search_result = MagicMock()
    mock_search_result.id = "chunk_1"
    mock_search_result.score = 0.85
    mock_search_result.payload = {
        "text": "Sample text",
        "url": "https://example.com",
        "title": "Example",
        "section": "Intro",
    }
    
    mock_qdrant_instance = MagicMock()
    mock_qdrant.return_value = mock_qdrant_instance
    mock_qdrant_instance.search.return_value = [mock_search_result]
    
    retriever = Retriever(config)
    results = retriever.retrieve("test query")
    
    assert len(results) == 1
    assert results[0]["text"] == "Sample text"
    assert results[0]["score"] == 0.85


def test_retriever_retrieve_empty_query():
    """Test retriever with empty query."""
    from backend.models.retriever import Retriever
    
    with patch("backend.models.retriever.QdrantClient"):
        with patch("backend.models.retriever.EmbeddingGenerator"):
            config = RAGConfig.from_env()
            retriever = Retriever(config)
            
            results = retriever.retrieve("")
            assert results == []


@patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
@patch("backend.models.llm.Groq")
def test_llm_generator_initialization(mock_groq):
    """Test LLM generator initialization."""
    from backend.models.llm import LLMGenerator
    
    config = RAGConfig.from_env()
    llm = LLMGenerator(config)
    
    assert llm.config == config
    assert llm.model == "mixtral-8x7b-32768"
    mock_groq.assert_called_once()


@patch.dict("os.environ", {"GROQ_API_KEY": ""})
def test_llm_generator_no_api_key():
    """Test LLM generator fails without API key."""
    from backend.models.llm import LLMGenerator
    
    config = RAGConfig.from_env()
    
    with pytest.raises(ValueError):
        LLMGenerator(config)


@patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
@patch("backend.models.llm.Groq")
def test_llm_generator_format_context(mock_groq):
    """Test context formatting."""
    from backend.models.llm import LLMGenerator
    
    config = RAGConfig.from_env()
    llm = LLMGenerator(config)
    
    chunks = [
        {
            "text": "Sample content",
            "url": "https://example.com",
            "title": "Example",
            "section": "Intro",
            "score": 0.85,
        }
    ]
    
    formatted = llm._format_context(chunks)
    
    assert "Sample content" in formatted
    assert "https://example.com" in formatted
    assert "Example" in formatted


@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_rag_agent_initialization(mock_llm, mock_retriever):
    """Test RAG agent initialization."""
    from backend.models.agent import RAGAgent
    
    config = RAGConfig.from_env()
    agent = RAGAgent(config)
    
    assert agent.config == config
    assert agent.query_count == 0
    assert len(agent.conversation_history) == 0


@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_rag_agent_query(mock_llm_class, mock_retriever_class):
    """Test RAG agent query processing."""
    from backend.models.agent import RAGAgent
    
    config = RAGConfig.from_env()
    
    # Mock retriever
    mock_retriever = MagicMock()
    mock_retriever_class.return_value = mock_retriever
    mock_retriever.retrieve.return_value = [
        {
            "text": "Retrieved context",
            "score": 0.85,
            "url": "https://example.com",
            "title": "Example",
            "section": "Intro",
        }
    ]
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.generate_with_context.return_value = "Generated response"
    
    agent = RAGAgent(config)
    result = agent.query("test question")
    
    assert result.query == "test question"
    assert result.response == "Generated response"
    assert len(result.retrieved_chunks) == 1
    assert agent.query_count == 1


@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_rag_agent_conversation_history(mock_llm_class, mock_retriever_class):
    """Test RAG agent conversation history."""
    from backend.models.agent import RAGAgent
    
    config = RAGConfig.from_env()
    
    mock_retriever = MagicMock()
    mock_retriever_class.return_value = mock_retriever
    mock_retriever.retrieve.return_value = []
    
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.generate_with_context.return_value = "Response"
    
    agent = RAGAgent(config)
    agent.query("Question 1", use_history=True)
    agent.query("Question 2", use_history=True)
    
    assert len(agent.conversation_history) == 4  # 2 user + 2 assistant
    assert agent.conversation_history[0]["role"] == "user"
    assert agent.conversation_history[0]["content"] == "Question 1"


@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_rag_agent_get_status(mock_llm_class, mock_retriever_class):
    """Test RAG agent status reporting."""
    from backend.models.agent import RAGAgent
    
    config = RAGConfig.from_env()
    
    mock_retriever = MagicMock()
    mock_retriever_class.return_value = mock_retriever
    mock_retriever.get_collection_info.return_value = {
        "name": "test_collection",
        "points_count": 100,
    }
    
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    
    agent = RAGAgent(config)
    status = agent.get_status()
    
    assert status["status"] == "active"
    assert status["queries_processed"] == 0
    assert status["collection"]["name"] == "test_collection"


@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_rag_agent_clear_history(mock_llm_class, mock_retriever_class):
    """Test clearing conversation history."""
    from backend.models.agent import RAGAgent
    
    config = RAGConfig.from_env()
    
    mock_retriever = MagicMock()
    mock_retriever_class.return_value = mock_retriever
    mock_retriever.retrieve.return_value = []
    
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.generate_with_context.return_value = "Response"
    
    agent = RAGAgent(config)
    agent.query("Question", use_history=True)
    
    assert len(agent.conversation_history) == 2
    
    agent.clear_history()
    assert len(agent.conversation_history) == 0


@patch("backend.models.orchestrator.run_indexing")
@patch("backend.models.agent.Retriever")
@patch("backend.models.agent.LLMGenerator")
def test_orchestrator_initialization(mock_llm, mock_retriever, mock_run_indexing):
    """Test RAG orchestrator initialization."""
    from backend.models.orchestrator import RAGOrchestrator, PipelineState
    
    config = RAGConfig.from_env()
    orchestrator = RAGOrchestrator(config)
    
    assert orchestrator.config == config
    assert orchestrator.pipeline_state == PipelineState.IDLE
    assert orchestrator.error_count == 0
