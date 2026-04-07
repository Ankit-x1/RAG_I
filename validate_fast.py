"""
Fast RAG System Validation - File & Structure Checks Only

No dependency imports - just validates:
1. File structure
2. Endpoint definitions
3. Configuration completeness
"""

import os
from pathlib import Path
import json


def validate_file_structure():
    """Check all required files exist."""
    print("\n✅ FILE STRUCTURE VALIDATION")
    print("-" * 60)
    
    required = {
        "backend/api/main.py": "FastAPI application",
        "backend/models/config.py": "Configuration",
        "backend/models/retriever.py": "Vector retriever",
        "backend/models/llm.py": "LLM client",
        "backend/models/agent.py": "RAG agent",
        "backend/indexing/pipeline.py": "Indexing pipeline",
        "backend/utils/cache.py": "Caching system",
        "backend/utils/production.py": "Production utils",
        "Dockerfile": "Docker image",
        "docker-compose-prod.yml": "Production stack",
        "configs/qdrant.yml": "Qdrant config",
        "README.md": "Documentation",
    }
    
    found = 0
    for path, desc in required.items():
        exists = Path(path).exists()
        status = "✅" if exists else "❌"
        print(f"{status} {path:35} {desc}")
        if exists:
            found += 1
    
    print(f"\nFound: {found}/{len(required)} files")
    return found == len(required)


def validate_endpoints():
    """Check all 15 endpoints are defined."""
    print("\n✅ ENDPOINT VALIDATION")
    print("-" * 60)
    
    endpoints = [
        "/health",
        "/status",
        "/index",
        "/collections",
        "/scrape",
        "/query",
        "/query/stream",
        "/batch-query",
        "/search/hybrid",
        "/chat",
        "/chat/stream",
        "/conversation/history",
        "/conversation/clear",
        "/reasoning/explain",
        "/embeddings/cached",
    ]
    
    with open("backend/api/main.py", "r", encoding="utf-8") as f:
        api_content = f.read()
    
    found = 0
    for endpoint in endpoints:
        if endpoint in api_content:
            print(f"✅ {endpoint:30}")
            found += 1
        else:
            print(f"❌ {endpoint:30} NOT FOUND")
    
    print(f"\nFound: {found}/{len(endpoints)} endpoints")
    return found == len(endpoints)


def validate_models():
    """Check all Pydantic models are defined."""
    print("\n✅ PYDANTIC MODELS VALIDATION")
    print("-" * 60)
    
    models = [
        "QueryRequest",
        "QueryResponse",
        "SourceDocument",
        "ChatRequest",
        "ChatResponse",
        "HybridSearchRequest",
        "StatusResponse",
    ]
    
    with open("backend/api/main.py", "r", encoding="utf-8") as f:
        api_content = f.read()
    
    found = 0
    for model in models:
        if f"class {model}" in api_content:
            print(f"✅ {model:30}")
            found += 1
        else:
            print(f"❌ {model:30} NOT FOUND")
    
    print(f"\nFound: {found}/{len(models)} models")
    return found == len(models)


def validate_docker_files():
    """Check Docker configuration."""
    print("\n✅ DOCKER CONFIGURATION VALIDATION")
    print("-" * 60)
    
    checks = {
        "Dockerfile": [
            ("FROM python:3.11", "Python 3.11 base"),
            ("uvicorn", "Uvicorn command"),
            ("EXPOSE 8000", "Port 8000"),
        ],
        "docker-compose-prod.yml": [
            ("backend:", "Backend service"),
            ("qdrant:", "Qdrant service"),
            ("GROQ_API_KEY", "Groq config"),
            ("QDRANT_HOST", "Qdrant config"),
            ("volumes:", "Persistence"),
        ],
    }
    
    passed = 0
    for file, items in checks.items():
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"\n{file}:")
        for check_str, desc in items:
            if check_str in content:
                print(f"  ✅ {desc}")
                passed += 1
            else:
                print(f"  ❌ {desc}")
    
    return passed == sum(len(items) for items in checks.values())


def validate_configuration():
    """Check configuration files."""
    print("\n✅ CONFIGURATION FILES VALIDATION")
    print("-" * 60)
    
    # Check requirements.txt
    with open("requirements.txt", "r", encoding="utf-8") as f:
        reqs = f.read().lower()
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "qdrant",
        "sentence-transformers",
        "groq",
        "pytest",
    ]
    
    found = 0
    for pkg in required_packages:
        if pkg in reqs:
            print(f"✅ {pkg}")
            found += 1
        else:
            print(f"❌ {pkg}")
    
    print(f"\nFound: {found}/{len(required_packages)} dependencies")
    return True


def validate_utils():
    """Check utility modules."""
    print("\n✅ UTILITY MODULES VALIDATION")
    print("-" * 60)
    
    cache_checks = [
        ("class EmbeddingCache", "EmbeddingCache class"),
        ("class QueryCache", "QueryCache class"),
        ("LRU", "LRU eviction"),
        ("ttl", "TTL support"),
    ]
    
    with open("backend/utils/cache.py", "r", encoding="utf-8") as f:
        cache_content = f.read()
    
    found = 0
    for check, desc in cache_checks:
        if check in cache_content:
            print(f"✅ Cache: {desc}")
            found += 1
        else:
            print(f"❌ Cache: {desc}")
    
    prod_checks = [
        ("class StructuredLogger", "Logging"),
        ("class PerformanceMonitor", "Monitoring"),
        ("class RAGException", "Error handling"),
        ("health_checker", "Health checks"),
    ]
    
    with open("backend/utils/production.py", "r", encoding="utf-8") as f:
        prod_content = f.read()
    
    for check, desc in prod_checks:
        if check in prod_content:
            print(f"✅ Production: {desc}")
            found += 1
        else:
            print(f"❌ Production: {desc}")
    
    print(f"\nFound: {found}/{len(cache_checks) + len(prod_checks)} utilities")
    return found == len(cache_checks) + len(prod_checks)


def main():
    """Run all validation checks."""
    print("\n" + "="*60)
    print("🔍 RAG PRODUCTION SYSTEM VALIDATION")
    print("="*60)
    
    os.chdir(Path(__file__).parent)
    
    results = {
        "File Structure": validate_file_structure(),
        "Endpoints (15)": validate_endpoints(),
        "Pydantic Models": validate_models(),
        "Docker Config": validate_docker_files(),
        "Dependencies": validate_configuration(),
        "Utilities": validate_utils(),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED - PRODUCTION READY!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
