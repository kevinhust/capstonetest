import logging
from typing import Optional
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class EmbeddingSingleton:
    """
    Singleton for holding the shared Embedding Function.
    Prevents redundant loading of the SentenceTransformer model (all-MiniLM-L6-v2),
    significantly reducing memory usage in the Swarm.
    """
    _instance: Optional[embedding_functions.SentenceTransformerEmbeddingFunction] = None

    @classmethod
    def get_instance(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._instance is None:
            logger.info(f"🧠 Loading EmbeddingSingleton instance ({model_name})...")
            try:
                cls._instance = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name
                )
                logger.info("✅ Embedding model loaded successfully into shared memory.")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                raise e
        return cls._instance
