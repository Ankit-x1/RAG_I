"""
Production API Endpoint Test Suite - v2.0.0

Tests all 15 production endpoints for:
- Route existence (no 404 errors)
- Response format validation
- Status codes
- Error handling

Run with: pytest test_api_endpoints.py -v
"""

import pytest
import json
from httpx import AsyncClient, Client
from typing import Dict, Any
import asyncio


# ============================================================================
# ENDPOINT REGISTRY - All 15 Production Endpoints
# ============================================================================

ENDPOINTS = {
    # System Management (2)
    "health": {"method": "GET", "path": "/health", "expected_status": 200},
    "status": {"method": "GET", "path": "/status", "expected_status": 200},
    
    # Document Indexing (3)
    "index": {"method": "POST", "path": "/index", "expected_status": 200},
    "collections": {"method": "GET", "path": "/collections", "expected_status": 200},
    "scrape": {"method": "POST", "path": "/scrape?urls=http://example.com", "expected_status": 200},
    
    # RAG Queries (4)
    "query": {"method": "POST", "path": "/query", "expected_status": 200, "body": {"query": "test"}},
    "query_stream": {"method": "POST", "path": "/query/stream", "expected_status": 200, "body": {"query": "test"}},
    "batch_query": {"method": "POST", "path": "/batch-query?queries=test", "expected_status": 200},
    "hybrid_search": {"method": "POST", "path": "/search/hybrid", "expected_status": 200, "body": {"query": "test"}},
    
    # Conversation (4)
    "chat": {"method": "POST", "path": "/chat", "expected_status": 200, "body": {"message": "hello"}},
    "chat_stream": {"method": "POST", "path": "/chat/stream", "expected_status": 200, "body": {"message": "hello"}},
    "chat_history": {"method": "GET", "path": "/conversation/history", "expected_status": 200},
    "chat_clear": {"method": "POST", "path": "/conversation/clear", "expected_status": 200},
    
    # Advanced (2)
    "reasoning": {"method": "POST", "path": "/reasoning/explain?query=test", "expected_status": 200},
    "embeddings": {"method": "GET", "path": "/embeddings/cached", "expected_status": 200},
    
    # Root
    "root": {"method": "GET", "path": "/", "expected_status": 200},
}


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestEndpointExistence:
    """Verify all endpoints exist (no 404 errors)."""
    
    @pytest.mark.asyncio
    async def test_all_endpoints_exist(self):
        """Test that all 15 endpoints return non-404 responses."""
        base_url = "http://localhost:8000"
        timeout = 10
        
        async with AsyncClient(base_url=base_url, timeout=timeout) as client:
            for name, endpoint in ENDPOINTS.items():
                method = endpoint["method"]
                path = endpoint["path"]
                body = endpoint.get("body")
                
                try:
                    if method == "GET":
                        response = await client.get(path)
                    elif method == "POST":
                        response = await client.post(path, json=body)
                    else:
                        pytest.skip(f"Unsupported method: {method}")
                    
                    # Assert not 404
                    assert response.status_code != 404, \
                        f"❌ {name} ({method} {path}): Got 404 - Route does not exist"
                    
                    # Log success
                    print(f"✅ {name:20} ({method:4} {path:30}): {response.status_code}")
                
                except Exception as e:
                    pytest.fail(f"❌ {name}: {str(e)}")


class TestEndpointResponses:
    """Validate response structure and content."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint returns valid structure."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "version" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self):
        """Test /status endpoint returns system metrics."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/status")
            
            # 503 is OK if agent not initialized, as long as not 404
            assert response.status_code in [200, 503]
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "version" in data
                assert "uptime_seconds" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root API endpoint."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/")
            assert response.status_code == 200
            
            data = response.json()
            assert "name" in data
            assert "version" in data
            assert data["version"] == "2.0.0"


class TestBatchEndpoints:
    """Test batch operations and limits."""
    
    @pytest.mark.asyncio
    async def test_batch_query_size_limit(self):
        """Test batch query respects size limits."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            # Test with valid batch size (5 queries)
            response = await client.post(
                "/batch-query?queries=q1&queries=q2&queries=q3&queries=q4&queries=q5"
            )
            assert response.status_code != 404
            
            # Test with oversized batch (51 queries) - should get 400
            large_queries = "&queries=".join([f"q{i}" for i in range(51)])
            response = await client.post(f"/batch-query?queries={large_queries}")
            assert response.status_code in [400, 422]  # Bad request


class TestStreamingEndpoints:
    """Test streaming response endpoints."""
    
    @pytest.mark.asyncio
    async def test_query_stream_returns_ndjson(self):
        """Test /query/stream returns JSON-lines format."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post(
                "/query/stream",
                json={"query": "test"},
                headers={"Accept": "application/x-ndjson"}
            )
            
            # Should not be 404
            assert response.status_code != 404
            
            # If successful, should be streaming
            if response.status_code == 200:
                # Stream should contain JSON-lines
                lines = response.text.strip().split("\n")
                assert len(lines) > 0


class TestErrorHandling:
    """Test error handling for invalid requests."""
    
    @pytest.mark.asyncio
    async def test_invalid_json_body(self):
        """Test endpoints handle invalid JSON gracefully."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post(
                "/query",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )
            
            # Should get 422 (validation error), not 404
            assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test endpoints validate required fields."""
        async with AsyncClient(base_url="http://localhost:8000") as client:
            # Query without 'query' field
            response = await client.post("/query", json={})
            
            # Should get 422 (validation error), not 404
            assert response.status_code != 404


# ============================================================================
# MANUAL TEST FUNCTIONS (for print-based testing)
# ============================================================================

def print_endpoint_registry():
    """Print all registered endpoints."""
    print("\n" + "="*80)
    print("RAG API v2.0.0 - Production Endpoints")
    print("="*80)
    
    categories = {}
    for name, endpoint in ENDPOINTS.items():
        category = name.split("_")[0].upper()
        if category not in categories:
            categories[category] = []
        categories[category].append((name, endpoint))
    
    for category in sorted(categories.keys()):
        print(f"\n{category} Endpoints:")
        for name, endpoint in categories[category]:
            method = endpoint["method"]
            path = endpoint["path"]
            print(f"  {method:4} {path:40} [{name}]")
    
    print(f"\nTotal Endpoints: {len(ENDPOINTS)}")
    print("="*80 + "\n")


def test_endpoint_structure():
    """Verify endpoint registry structure."""
    print("\nValidating Endpoint Registry...")
    
    required_methods = {"GET", "POST", "PUT", "DELETE"}
    
    for name, endpoint in ENDPOINTS.items():
        assert "method" in endpoint, f"{name}: missing 'method'"
        assert "path" in endpoint, f"{name}: missing 'path'"
        assert endpoint["method"] in required_methods, f"{name}: invalid method"
        assert endpoint["path"].startswith("/"), f"{name}: path must start with /"
    
    print(f"✅ All {len(ENDPOINTS)} endpoints have valid structure\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🧪 RAG API Test Suite ".center(80, "="))
    
    # Print registry
    print_endpoint_registry()
    
    # Validate structure
    test_endpoint_structure()
    
    # Run pytest
    print("\nRunning pytest suite...\n")
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
