"""
Script to populate Elasticsearch knowledge base with sample failure cases.

This script loads sample failure cases from sample_data.json and indexes them
into Elasticsearch using the Indexing Service API.
"""

import json
import asyncio
import httpx
from pathlib import Path


INDEXING_SERVICE_URL = "http://localhost:8003"
SAMPLE_DATA_FILE = Path(__file__).parent / "sample_data.json"


async def load_sample_data():
    """Load sample data from JSON file."""
    with open(SAMPLE_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def index_document(client: httpx.AsyncClient, document: dict) -> dict:
    """Index a single document via Indexing Service API."""
    try:
        response = await client.post(
            f"{INDEXING_SERVICE_URL}/index",
            json=document,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"❌ Failed to index document '{document['title']}': {e}")
        return None


async def populate_knowledge_base():
    """Populate knowledge base with sample failure cases."""
    print("=" * 80)
    print("🚀 Populating Knowledge Base with Sample Failure Cases")
    print("=" * 80)
    print()
    
    # Load sample data
    print("📂 Loading sample data from sample_data.json...")
    try:
        documents = await load_sample_data()
        print(f"✅ Loaded {len(documents)} documents")
        print()
    except Exception as e:
        print(f"❌ Failed to load sample data: {e}")
        return
    
    # Check Indexing Service health
    print("🔍 Checking Indexing Service health...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{INDEXING_SERVICE_URL}/health", timeout=10.0)
            response.raise_for_status()
            health = response.json()
            print(f"✅ Indexing Service: {health['status']}")
            print(f"   - Elasticsearch: {'✅' if health['elasticsearch_connected'] else '❌'}")
            print(f"   - Model Loaded: {'✅' if health['model_loaded'] else '❌'}")
            print()
        except Exception as e:
            print(f"❌ Failed to connect to Indexing Service: {e}")
            print(f"   Make sure the service is running on {INDEXING_SERVICE_URL}")
            return
    
    # Index documents
    print(f"📝 Indexing {len(documents)} documents...")
    print()
    
    async with httpx.AsyncClient() as client:
        success_count = 0
        failed_count = 0
        
        for i, doc in enumerate(documents, 1):
            print(f"[{i}/{len(documents)}] Indexing: {doc['title'][:60]}...")
            result = await index_document(client, doc)
            
            if result:
                success_count += 1
                print(f"   ✅ Indexed with ID: {result['id']}")
            else:
                failed_count += 1
            print()
        
        print("=" * 80)
        print("📊 Indexing Summary")
        print("=" * 80)
        print(f"✅ Successfully indexed: {success_count}/{len(documents)}")
        if failed_count > 0:
            print(f"❌ Failed: {failed_count}/{len(documents)}")
        print()
        
        # Get stats
        print("📈 Knowledge Base Statistics:")
        try:
            response = await client.get(f"{INDEXING_SERVICE_URL}/stats", timeout=10.0)
            response.raise_for_status()
            stats = response.json()
            print(f"   - Index: {stats['index']}")
            print(f"   - Document Count: {stats['document_count']}")
            print(f"   - Size: {stats['size_bytes'] / 1024 / 1024:.2f} MB")
            print(f"   - Embedding Model: {stats['embedding_model']}")
            print(f"   - Embedding Dimension: {stats['embedding_dimension']}")
        except Exception as e:
            print(f"   ⚠️  Could not retrieve stats: {e}")
        
        print()
        print("=" * 80)
        print("✨ Knowledge base population complete!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(populate_knowledge_base())
