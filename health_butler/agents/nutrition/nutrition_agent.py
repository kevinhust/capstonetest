
"""Nutrition Agent for food analysis and diet advice.

This specialist agent analyzes food items from text or images,
estimates calories/macros, and provides health tips using RAG
and vision tools.
"""

from typing import Optional, List, Dict, Any
import logging
from src.agents.base_agent import BaseAgent
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.cv_food_rec.gemini_vision_engine import GeminiVisionEngine
from health_butler.data_rag.rag_tool import RagTool

logger = logging.getLogger(__name__)

class NutritionAgent(BaseAgent):
    """
    Specialist agent for analyzing food, calculating nutrition, and providing diet advice.
    
    Hybrid Vision (Phase 5):
    - YOLOv8: Detects boundaries and objects.
    - Gemini 2.5 Flash: Performs detailed semantic analysis (ingredients, portions).
    - RAG: Provides supplementary USDA/Common Foods data.
    """
    
    def __init__(self, vision_tool: Optional[VisionTool] = None):
        super().__init__(
            role="nutrition",
            system_prompt="""You are an expert Nutritionist and Dietitian AI.
            
Your responsibilities:
1. Identify food items from descriptions or analyzed image analysis.
2. Estimate calories and macronutrients (Protein, Carbs, Fat) with high accuracy.
3. Provide breakdown of ingredients when possible.
4. Offer brief, actionable health tips based on the food content.

When you don't know the exact nutrition, use your general knowledge but mention it is an estimate.
If provided with tool outputs (like RAG search results), prioritize that data.
            """
        )
        # Use shared vision tool if provided (Singleton pattern anyway)
        self.vision_tool = vision_tool or VisionTool()
        self.gemini_engine = GeminiVisionEngine()
        self.rag_tool = RagTool()

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute nutrition analysis using Hybrid Vision System (Synchronous).
        """
        logger.info("[NutritionAgent] Executing task: %s", task)
        
        # Check for image path and user context
        image_path = None
        user_context_str = ""
        if context:
            for msg in context:
                if msg.get("type") == "image_path":
                    image_path = msg.get("content")
                elif msg.get("type") == "user_context":
                    user_context_str = msg.get("content")
        
        vision_context = ""
        if image_path:
            logger.info("[NutritionAgent] Starting Hybrid Vision Analysis...")
            
            # Step 1: Detect boundaries (YOLO)
            detections = self.vision_tool.detect_food(image_path)
            detections_summary = f"YOLO detected {len(detections)} potential food objects."
            
            # Step 2: Semantic Analysis (Gemini)
            gemini_result = self.gemini_engine.analyze_food(image_path, user_context_str)
            
            if "error" not in gemini_result:
                # Format vision context for the LLM
                items = gemini_result.get("items", [])
                if items:
                    main_item = items[0]
                    vision_context = (
                        f"Visual Analysis Summary:\n"
                        f"- Dish: {main_item.get('name')}\n"
                        f"- Total Calories: {gemini_result.get('total_estimated_calories')} kcal\n"
                        f"- Ingredients: {', '.join([i['name'] for i in main_item.get('ingredients', [])])}\n"
                        f"- Tip: {gemini_result.get('health_tip')}\n"
                    )
                    # Sync detected label for RAG lookup
                    task = f"{task}. logic: Analyze {main_item.get('name')}."
            else:
                vision_context = f"(Vision analysis failed: {gemini_result.get('error')})"
        
        # Step 3: RAG Lookup (Supplementary & Verification)
        # Use the Gemini-verified dish name for targetted search, or fallback to the task string
        query_text = task
        if vision_context and "main_item" in locals():
            query_text = main_item.get('name', task)
            
        rag_results = self.rag_tool.query(query_text, top_k=3)
        rag_context = ""
        if rag_results:
            rag_context = "\nUSDA/Knowledge Base Details:\n"
            for res in rag_results:
                rag_context += f"- {res['text']}\n"
        
        # Augment the prompt with everything we have
        augmented_task = f"{task}\n\n{vision_context}\n{rag_context}"
        
        # Call the base agent (LLM) to synthesize the final friendly response
        return super().execute(augmented_task, context)
