"""Enhanced RAG Tool for safety-first health retrieval.

Combines semantic search (ChromaDB) with structured safety filtering
based on user health conditions and exercise contraindications.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from health_butler.data_rag.rag_tool import RagTool

# Setup logging
logger = logging.getLogger(__name__)

class EnhancedRagTool(RagTool):
    """
    Enhanced RAG tool with Phase 5 safety filtering integration.
    Manages both specialized JSON datasets and vector search.
    """
    
    def __init__(self, 
                 db_path: str = "health_butler/data/chroma_db", 
                 collection_name: str = "nutrition_data",
                 data_dir: str = "health_butler/data/rag"):
        super().__init__(db_path, collection_name)
        self.data_dir = data_dir
        self.exercises = self._load_json("exercises.json")
        self.safety_protocols = self._load_json("safety_protocols.json")
        logger.info(f"EnhancedRagTool initialized with {len(self.exercises)} exercises and {len(self.safety_protocols)} protocols.")

    def _load_json(self, filename: str) -> List[Dict[str, Any]]:
        """Load structured data from JSON files."""
        path = os.path.join(self.data_dir, filename)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            logger.warning(f"⚠️ Data file not found: {path}. Using empty list.")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to load {filename}: {e}")
            return []

    def get_safe_recommendations(self, 
                                 user_query: str, 
                                 user_conditions: List[str], 
                                 top_k: int = 5) -> Dict[str, Any]:
        """
        Three-layer safety filtering algorithm:
        1. Contextual matching (Query vs Exercise Bank)
        2. Impact-level filtering based on protocols
        3. Contraindication overlapping check
        """
        logger.info(f"🛡️ Smart Query for: '{user_query}' | Conditions: {user_conditions}")
        
        # Determine restrictions from protocols
        prohibited_patterns = []
        warnings = []
        for condition in user_conditions:
            for protocol in self.safety_protocols:
                if protocol["condition"].lower() == condition.lower():
                    prohibited_patterns.extend(protocol.get("forbidden_patterns", []))
                    warnings.append(protocol.get("warning_message", ""))

        safe_exercises = []
        filtered_count = 0
        
        # Filter exercise bank
        for ex in self.exercises:
            is_safe = True
            # Check contraindications
            for cond in user_conditions:
                if any(cond.lower() in contra.lower() for contra in ex.get("contraindications", [])):
                    is_safe = False
                    break
            
            # Check prohibited patterns (simple keyword match for now)
            if is_safe:
                for pattern in prohibited_patterns:
                    if pattern.lower() in ex["name"].lower() or pattern.lower() in ex.get("description", "").lower():
                        is_safe = False
                        break
            
            if is_safe:
                safe_exercises.append(ex)
            else:
                filtered_count += 1

        # Fallback to vector search for general info if no specific exercises found
        rag_results = []
        if not safe_exercises:
            rag_results = self.query(user_query, top_k=top_k)

        return {
            "safe_exercises": safe_exercises[:top_k],
            "safety_warnings": list(set(warnings)),
            "filtered_count": filtered_count,
            "semantic_results": rag_results
        }

if __name__ == "__main__":
    # Test logic
    logging.basicConfig(level=logging.INFO)
    tool = EnhancedRagTool()
    
    # Test Scenario: Knee Injury
    res = tool.get_safe_recommendations("I want to train legs", ["Knee Injury"])
    print("\n--- TEST: KNEE INJURY ---")
    print(f"Safe: {[e['name'] for e in res['safe_exercises']]}")
    print(f"Warnings: {res['safety_warnings']}")
    print(f"Filtered: {res['filtered_count']}")
