"""Gemini Vision Engine for semantic food analysis.

Uses Gemini 2.5 Flash to identify dishes, ingredients, and estimate portions.
Works in tandem with YOLOv8 which provides boundary detection.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from PIL import Image

# Setup logging
logger = logging.getLogger(__name__)

class GeminiVisionEngine:
    """
    Semantic engine for food analysis using Gemini.
    Responsible for "what" is in the image.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ GOOGLE_API_KEY not found. GeminiVisionEngine will fail.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"GeminiVisionEngine initialized with model: {model_name}")

    def analyze_food(self, image_path: str, user_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a food image using Gemini and return structured data (Synchronous).
        """
        if not self.api_key:
            return {"error": "API Key missing"}

        logger.info(f"🚀 Sending image to Gemini for semantic analysis: {image_path}")
        
        try:
            img = Image.open(image_path)
            
            prompt = """You are an expert nutritionist and chef. Analyze this food image in extreme detail.
... [Rest of the prompt remains same] ...
"""
            if user_context:
                prompt += f"\n\nUSER CONTEXT: {user_context}"

            # Call Gemini (Synchronous)
            response = self.model.generate_content([prompt, img])
            
            # Clean and parse JSON
            text = response.text
            # Remove markdown code blocks if any
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(text)
            logger.info("✅ Gemini analysis complete.")
            return data
            
        except Exception as e:
            logger.error(f"❌ Gemini analysis failed: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    # Test block
    import asyncio
    async def test():
        engine = GeminiVisionEngine()
        res = await engine.analyze_food("data/raw/sample_food.jpg")
        print(json.dumps(res, indent=2))
    
    # asyncio.run(test())
