"""RAG Tool using ChromaDB for semantic search.

Provides nutrition information retrieval using vector embeddings.
Uses SentenceTransformerEmbeddingFunction with all-MiniLM-L6-v2 model
for generating embeddings from food-related queries.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

# Setup logging
logger = logging.getLogger(__name__)

class RagTool:
    """
    RAG tool using ChromaDB for semantic search.
    Phase 2: ChromaDB + SentenceTransformers.
    """

    def __init__(self, db_path: str = "health_butler/data/chroma_db", collection_name: str = "nutrition_data"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.ef = None
        self.client = None
        self.collection = None
        logger.info("RagTool initialized (Lazy Loading enabled)")

    def _load_resources(self):
        """Lazy load embedding function and database connection."""
        if self.collection is not None:
            return

        try:
            # Initialize embedding function
            # Using a lightweight model for the MVP
            logger.info("Initializing SentenceTransformerEmbeddingFunction (all-MiniLM-L6-v2)...")
            self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Initialize ChromaDB
            path_obj = Path(self.db_path)
            path_obj.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.ef
            )
            logger.info("Connected to ChromaDB at %s, collection: %s", self.db_path, self.collection_name)
        except Exception as e:
            logger.error("Failed to initialize RagTool resources: %s", e)
            raise e

    def query(self, query_text: str, top_k: int = 3, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using semantic search.
        """
        self._load_resources()
        logger.info("RAG Query: %s", query_text)
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_metadata # Optional metadata filtering
            )
            
            # Format results
            formatted_results = []
            if results['documents']:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "id": results['ids'][0][i]
                    })
            
            return formatted_results

        except Exception as e:
            logger.error("Query failed: %s", str(e))
            return []

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to the vector DB.
        Expected format: [{"text": "...", "metadata": {...}, "id": "..."}]
        """
        self._load_resources()
        if not documents:
            return
            
        texts = [d['text'] for d in documents]
        metadatas = [d.get("metadata", {}) for d in documents]
        ids = [d.get('id', str(hash(d['text']))) for d in documents]

        try:
            self.collection.upsert(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("Upserted %d documents to ChromaDB.", len(documents))
        except Exception as e:
            logger.error("Failed to add documents: %s", e)

# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = RagTool()
    # Test adding a doc if empty
    if tool.collection.count() == 0:
        tool.add_documents([{
            "text": "Chicken breast is high in protein and low in fat.",
            "metadata": {"protein": 31, "category": "poultry"},
            "id": "chicken_breast"
        }])
        
    res = tool.query("healthy meat")
    print(res)
