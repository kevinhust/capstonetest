"""RAG Tool using ChromaDB for semantic search.

Provides nutrition information retrieval using vector embeddings.
Uses SentenceTransformerEmbeddingFunction via EmbeddingSingleton.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from health_butler.data_rag.embedding_singleton import EmbeddingSingleton

# Setup logging
logger = logging.getLogger(__name__)

class RagTool:
    """
    RAG tool using ChromaDB for semantic search.
    Phase 7: Integrated with EmbeddingSingleton for memory efficiency.
    """

    def __init__(self, db_path: str = "health_butler/data/chroma_db", collection_name: str = "nutrition_data"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.ef = EmbeddingSingleton.get_instance()
        self.client = None
        self.collection = None
        logger.info("RagTool initialized with shared EmbeddingSingleton")

    def _load_resources(self):
        """Lazy load database connection. Embedding function is now singleton."""
        if self.collection is not None:
            return

        try:
            # Initialize ChromaDB
            path_obj = Path(self.db_path)
            path_obj.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.ef # Uses the Ef from singleton
            )
            logger.info("Connected to ChromaDB at %s, collection: %s", self.db_path, self.collection_name)
        except Exception as e:
            logger.error("Failed to initialize RagTool resources: %s", e)
            raise e

    def query(self, query_text: str, top_k: int = 3, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._load_resources()
        logger.info("RAG Query: %s", query_text)
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_metadata
            )
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
        self._load_resources()
        if not documents: return
        texts = [d['text'] for d in documents]
        metadatas = [d.get("metadata", {}) for d in documents]
        ids = [d.get('id', str(hash(d['text']))) for d in documents]
        try:
            self.collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
            logger.info("Upserted %d documents to ChromaDB.", len(documents))
        except Exception as e:
            logger.error("Failed to add documents: %s", e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = RagTool()
    res = tool.query("healthy food")
    print(res)
