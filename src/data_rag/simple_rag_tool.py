"""Simple RAG Tool for reliable, memory-based safety and nutrition retrieval.

Replaces vector database complexity with direct JSON filtering for 
Capstone/MVP scale. Uses rapidfuzz for robust keyword matching.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

try:
    from rapidfuzz import process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)

class SimpleRagTool:
    """
    Lightweight RAG tool that loads JSONs into memory.
    Phase 7: Integrated with rapidfuzz for robust matching.
    Phase 11: Added nutritional database support.
    """
    
    def __init__(self, data_dir: str = "health_butler/data"):
        self.data_dir = data_dir
        self.exercises = self._load_json("rag/exercises.json")
        self.safety_protocols = self._load_json("rag/safety_protocols.json")
        
        # Load Nutritional Data
        self.usda_foods = self._load_json("raw/usda_common_foods.json")
        logger.info(f"✅ SimpleRagTool initialized: {len(self.exercises)} exercises, {len(self.usda_foods)} foods, {FUZZY_AVAILABLE=}")

    def _load_json(self, relative_path: str) -> List[Dict[str, Any]]:
        """Load structured data from JSON files."""
        potential_paths = [
            os.path.join(self.data_dir, relative_path),
            os.path.join(os.getcwd(), self.data_dir, relative_path),
            os.path.join(os.path.dirname(__file__), "..", "data", relative_path),
        ]
        for path in potential_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"❌ Failed to parse {path}: {e}")
                    return []
        
        # logger.warning(f"⚠️ Data file not found: {relative_path}")
        return []

    def search_food(self, query: str, min_score: int = 75, limit: int = 1) -> Optional[Dict[str, Any]]:
        """Search for food items with nutritional data."""
        if not self.usda_foods or not query:
            return None
        
        query = query.lower().strip()
        
        if FUZZY_AVAILABLE:
            # Search space: queries and descriptions
            search_space = [f"{f.get('query', '')} {f.get('description', '')}".lower() for f in self.usda_foods]
            
            results = process.extract(
                query,
                search_space,
                scorer=fuzz.WRatio,
                limit=limit
            )
            
            if results and results[0][1] >= min_score:
                idx = results[0][2]
                food_item = self.usda_foods[idx]
                
                # Normalize results
                nutrients = food_item.get("nutrients", {})
                return {
                    "name": food_item.get("description", "Unknown").title(),
                    "calories": nutrients.get("calories", {}).get("value", 0),
                    "protein": nutrients.get("protein", {}).get("value", 0),
                    "carbs": nutrients.get("carbs", {}).get("value", 0),
                    "fat": nutrients.get("fat", {}).get("value", 0),
                    "confidence": results[0][1],
                    "source": "USDA"
                }
        
        return None

    def search_exercises(self, query: str, min_score: int = 60, limit: int = 5) -> List[Dict]:
        """Search exercises with fuzzy matching logic."""
        query = query.lower().strip()
        if not query:
            return self.exercises[:limit]

        if FUZZY_AVAILABLE:
            search_space = []
            for ex in self.exercises:
                text = f"{ex.get('name', '')} {ex.get('category', '')} {' '.join(ex.get('tags', []))}".lower()
                search_space.append(text)
            
            results = process.extract(
                query,
                search_space,
                scorer=fuzz.WRatio,
                limit=limit * 2
            )
            
            matched = []
            for res in results:
                score = res[1]
                idx = res[2]
                if score >= min_score:
                    matched.append(self.exercises[idx])
            return matched[:limit]
        
        return []

    def get_safe_recommendations(self, 
                                 user_query: str, 
                                 user_conditions: List[str], 
                                 top_k: int = 5) -> Dict[str, Any]:
        """Safety-First Retrieval Algorithm."""
        active_conditions = [c.lower() for c in user_conditions]
        
        # Filter logic remains same
        safe_list = []
        for ex in self.exercises:
            is_safe = True
            for contra in ex.get("contraindications", []):
                if contra.lower() in active_conditions:
                    is_safe = False; break
            if is_safe: safe_list.append(ex)

        original_exercises = self.exercises
        self.exercises = safe_list
        recs = self.search_exercises(user_query, limit=top_k)
        self.exercises = original_exercises

        return {"safe_exercises": recs}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = SimpleRagTool()
    # Test food search
    test_food = "pork ribs"
    res = tool.search_food(test_food)
    if res:
        print(f"✅ RAG Food Search found: {res['name']} | Calories: {res['calories']}")
    else:
        print(f"❌ RAG Food Search failed for: {test_food}")
