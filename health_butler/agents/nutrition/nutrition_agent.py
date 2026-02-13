import logging
import json
import re
from typing import Optional, List, Dict, Any
from src.agents.base_agent import BaseAgent
from src.config import settings
from google.genai.types import GenerateContentConfig
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.cv_food_rec.gemini_vision_engine import GeminiVisionEngine
from health_butler.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

class NutritionAgent(BaseAgent):
    """
    Specialist agent for food analysis.
    
    Phase 11: RAG Nutritional Integration.
    - Uses SimpleRagTool.search_food to anchor vision estimates in ground truth.
    """
    
    def __init__(self, vision_tool: Optional[VisionTool] = None):
        super().__init__(
            role="nutrition",
            system_prompt="""You are an expert Nutritionist AI.
Your goal is to synthesize food analysis into a structured format.

OUTPUT FORMAT:
You MUST return a valid JSON object:
{
  "dish_name": "Main dish identified",
  "total_macros": {
    "calories": 0,
    "protein": 0,
    "carbs": 0,
    "fat": 0
  },
  "confidence_score": 0.0,
  "composition_analysis": "Detailed breakdown of ingredients and portions.",
  "health_tip": "A brief actionable tip.",
    "items_detected": [],
    "calorie_breakdown": [
        {
            "item": "Avocado",
            "quantity": 1,
            "calories_each": 160,
            "calories_total": 160
        }
    ]
}

CRITICAL RULES:
- Use 'RAG_MATCHES' to ground your 'total_macros' calculation.
- If a high-confidence RAG match exists, prioritize its per-100g data calibrated by the estimated portion size.
- DO NOT return 0 for macros if food is detected.
""",
            use_openai_api=False
        )
        self.vision_tool = vision_tool or VisionTool()
        self.gemini_engine = GeminiVisionEngine()
        self.rag = SimpleRagTool()

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Robustly extract JSON from a string."""
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                return json.loads(text[first_brace:last_brace+1])
            return None
        except Exception as e:
            logger.error(f"[NutritionAgent] JSON extraction failed: {e}")
            return None

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """Convert arbitrary values to float safely."""
        try:
            return float(value)
        except Exception:
            return default

    def _parse_quantity(self, portion_text: str) -> int:
        """Infer quantity from portion text like 'x3', '3 pieces', or '2x'."""
        if not portion_text:
            return 1

        text = str(portion_text).lower()
        patterns = [
            r"x\s*(\d+)",
            r"(\d+)\s*x",
            r"(\d+)\s*(?:pieces?|items?|slices?|servings?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return max(1, int(match.group(1)))
                except Exception:
                    continue
        return 1

    def _build_calorie_breakdown(
        self,
        items: List[Dict[str, Any]],
        rag_matches: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build per-item calorie estimates plus subtotal using vision + RAG data."""
        breakdown: List[Dict[str, Any]] = []

        def aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            grouped: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                item_name = str(row.get("item") or "Unknown").strip()
                qty = max(1, int(self._to_float(row.get("quantity"), 1)))
                total = self._to_float(row.get("calories_total"), 0.0)
                if total <= 0:
                    continue

                if item_name not in grouped:
                    grouped[item_name] = {
                        "item": item_name,
                        "quantity": 0,
                        "calories_total": 0.0,
                    }
                grouped[item_name]["quantity"] += qty
                grouped[item_name]["calories_total"] += total

            output: List[Dict[str, Any]] = []
            for item_name, row in grouped.items():
                qty = row["quantity"]
                c_total = round(row["calories_total"], 1)
                output.append(
                    {
                        "item": item_name,
                        "quantity": qty,
                        "calories_each": round(c_total / qty, 1),
                        "calories_total": c_total,
                    }
                )
            return output

        rag_by_original: Dict[str, Dict[str, Any]] = {}
        for match in rag_matches or []:
            original_name = str(match.get("original_item") or "").strip().lower()
            if original_name and original_name not in rag_by_original:
                rag_by_original[original_name] = match

        for item in items or []:
            if not isinstance(item, dict):
                continue

            item_name = str(item.get("name") or "Unknown").strip()
            item_key = item_name.lower()
            portion_text = str(item.get("portion") or "")
            quantity = self._parse_quantity(portion_text)
            estimated_grams = self._to_float(item.get("estimated_weight_grams"), 0.0)

            rag_match = rag_by_original.get(item_key)
            calories_per_100g = self._to_float((rag_match or {}).get("calories"), 0.0)
            vision_calories = self._to_float((item.get("macros") or {}).get("calories"), 0.0)

            calories_each = 0.0
            calories_total = 0.0

            if calories_per_100g > 0 and estimated_grams > 0:
                calories_each = round((calories_per_100g * estimated_grams) / 100.0, 1)
                calories_total = round(calories_each * quantity, 1)
            elif vision_calories > 0:
                calories_total = round(vision_calories, 1)
                calories_each = round(calories_total / quantity, 1)
            elif calories_per_100g > 0:
                calories_each = round(calories_per_100g, 1)
                calories_total = round(calories_each * quantity, 1)

            if calories_total <= 0:
                continue

            breakdown.append(
                {
                    "item": item_name,
                    "quantity": int(quantity),
                    "calories_each": calories_each,
                    "calories_total": calories_total,
                }
            )

        if breakdown:
            return aggregate_rows(breakdown)

        for match in rag_matches[:6]:
            name = str(match.get("original_item") or match.get("name") or "Unknown")
            calories = round(self._to_float(match.get("calories"), 0.0), 1)
            if calories <= 0:
                continue
            breakdown.append(
                {
                    "item": name,
                    "quantity": 1,
                    "calories_each": calories,
                    "calories_total": calories,
                }
            )

        return aggregate_rows(breakdown)

    def _sum_macros_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate macro totals from vision-detected items when available."""
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for item in items or []:
            macros = item.get("macros", {}) if isinstance(item, dict) else {}
            for key in totals:
                try:
                    totals[key] += float(macros.get(key, 0) or 0)
                except Exception:
                    continue
        return totals

    def _sum_macros_from_rag(self, rag_matches: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate macro totals from RAG matches."""
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for match in rag_matches or []:
            for key in totals:
                try:
                    totals[key] += float(match.get(key, 0) or 0)
                except Exception:
                    continue
        return totals

    def _build_fallback_payload(
        self,
        vision_info: Dict[str, Any],
        rag_matches: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a non-zero nutrition payload when synthesis fails."""
        rag_totals = self._sum_macros_from_rag(rag_matches)
        item_totals = self._sum_macros_from_items(items)

        totals = rag_totals if rag_totals.get("calories", 0) > 0 else item_totals

        dish_name = vision_info.get("dish_name")
        if not dish_name and items:
            first_name = items[0].get("name") if isinstance(items[0], dict) else None
            dish_name = first_name or "Meal"

        if totals.get("calories", 0) <= 0:
            return {
                "dish_name": dish_name or "Meal",
                "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                "detailed_nutrients": {
                    "sodium_mg": 0,
                    "fiber_g": 0,
                    "sugar_g": 0,
                    "saturated_fat_g": 0,
                },
                "confidence_score": vision_info.get("total_confidence", vision_info.get("confidence_score", 0.6)),
                "composition_analysis": "Nutrition data is limited for this item. Try another image angle for better analysis.",
                "health_tip": "Keep portions balanced and pair fruit with a protein source for better satiety.",
                "ingredients_with_portions": [m.get("name", "Unknown") for m in rag_matches[:5]] if rag_matches else [],
                "items_detected": [item.get("name", "Unknown") if isinstance(item, dict) else str(item) for item in items[:5]],
                "calorie_breakdown": self._build_calorie_breakdown(items, rag_matches),
            }

        ingredients = [
            f"{m.get('original_item', m.get('name', 'Unknown'))} (~{m.get('estimated_portion', '1 serving')})"
            for m in rag_matches[:6]
        ]
        if not ingredients:
            ingredients = [
                item.get("name", "Unknown") if isinstance(item, dict) else str(item)
                for item in items[:6]
            ]

        return {
            "dish_name": dish_name or "Meal",
            "total_macros": {k: round(v, 1) for k, v in totals.items()},
            "detailed_nutrients": {
                "sodium_mg": 0,
                "fiber_g": 0,
                "sugar_g": 0,
                "saturated_fat_g": 0,
            },
            "confidence_score": vision_info.get("total_confidence", vision_info.get("confidence_score", 0.85)),
            "composition_analysis": "Estimated from visual food recognition anchored with USDA/RAG nutritional references.",
            "health_tip": "Meal analyzed successfully. Balance remaining meals today with fiber-rich vegetables and hydration.",
            "ingredients_with_portions": ingredients,
            "items_detected": [item.get("name", "Unknown") if isinstance(item, dict) else str(item) for item in items[:6]],
            "calorie_breakdown": self._build_calorie_breakdown(items, rag_matches),
        }

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute nutrition analysis with RAG grounding.
        """
        logger.info("[NutritionAgent] Executing nutrition synthesis with RAG grounding...")
        
        image_path = None
        user_context_str = "{}"
        if context:
            for msg in context:
                if msg.get("type") == "image_path":
                    image_path = msg.get("content")
                elif msg.get("type") == "user_context":
                    user_context_str = msg.get("content", "{}")
        
        vision_info = {}
        if image_path:
            vision_result = self.gemini_engine.analyze_food(image_path, user_context_str)
            if "error" not in vision_result:
                vision_info = vision_result
            else:
                logger.error(f"[NutritionAgent] Vision analysis failed: {vision_result.get('error')}")
        
        # Phase 11: RAG Grounding
        rag_matches = []
        items = vision_info.get("items", [])
        if not items and vision_info.get("dish_name"):
            items = [{"name": vision_info["dish_name"], "portion": "1 serving"}]
            
        for item in items:
            name = item.get("name", "")
            match = self.rag.search_food(name)
            if match:
                match["original_item"] = name
                match["estimated_portion"] = item.get("portion", "unknown")
                rag_matches.append(match)
                logger.info(f"[NutritionAgent] RAG Match Found: {match['name']} for {name}")

        # Final Synthesis Prompt
        synthesis_input = f"""
TASK: {task}
VISION_RESULT: {json.dumps(vision_info)}
RAG_MATCHES (Ground Truth Data): {json.dumps(rag_matches)}

Synthesize the final nutritional analysis. 
IMPORTANT: 
- If RAG_MATCHES or VISION_RESULT contains calorie/macro data, 'total_macros' MUST reflect this. NEVER return 0 if food is visible.
- Use the RAG_MATCHES as the most reliable source for 'per 100g' data, scaling by the portion size estimated in VISION_RESULT.
- Ensure the 'composition_analysis' explains exactly why these specific numbers were chosen.
- For 'ingredients_with_portions', estimate weight/quantity (e.g., '135g x3', '270g total').
- For 'detailed_nutrients', provide estimates for Sodium (mg), Fiber (g), Sugar (g), and Saturated Fat (g) based on common nutritional data.
"""
        
        data = None
        model_candidates = [settings.GEMINI_MODEL_NAME, "gemini-2.5-flash"]
        for model_name in model_candidates:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=self.system_prompt + "\n\n" + synthesis_input,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={
                            "type": "OBJECT",
                            "properties": {
                                "dish_name": {"type": "STRING"},
                                "total_macros": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "calories": {"type": "NUMBER"},
                                        "protein": {"type": "NUMBER"},
                                        "carbs": {"type": "NUMBER"},
                                        "fat": {"type": "NUMBER"}
                                    },
                                    "required": ["calories", "protein", "carbs", "fat"]
                                },
                                "detailed_nutrients": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "sodium_mg": {"type": "NUMBER"},
                                        "fiber_g": {"type": "NUMBER"},
                                        "sugar_g": {"type": "NUMBER"},
                                        "saturated_fat_g": {"type": "NUMBER"}
                                    }
                                },
                                "confidence_score": {"type": "NUMBER"},
                                "composition_analysis": {"type": "STRING"},
                                "health_tip": {"type": "STRING"},
                                "ingredients_with_portions": {
                                    "type": "ARRAY", 
                                    "items": {"type": "STRING"}
                                },
                                "items_detected": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "calorie_breakdown": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "item": {"type": "STRING"},
                                            "quantity": {"type": "NUMBER"},
                                            "calories_each": {"type": "NUMBER"},
                                            "calories_total": {"type": "NUMBER"}
                                        }
                                    }
                                }
                            },
                            "required": ["dish_name", "total_macros", "composition_analysis", "ingredients_with_portions"]
                        }
                    )
                )
                data = response.parsed
                if model_name != settings.GEMINI_MODEL_NAME:
                    logger.info(f"[NutritionAgent] Structured synthesis recovered with fallback model: {model_name}")
                break
            except Exception as e:
                logger.error(f"[NutritionAgent] Structured synthesis failed on {model_name}: {e}")

        if data is None:
            # Text fallback
            result_str = super().execute(synthesis_input, context)
            data = self._extract_json(result_str)
        
        if data:
            # Numeric safety
            if "total_macros" in data:
                for target in ["calories", "protein", "carbs", "fat"]:
                    val = data["total_macros"].get(target, 0)
                    try: data["total_macros"][target] = float(val) if val is not None else 0
                    except: data["total_macros"][target] = 0

            calorie_breakdown = self._build_calorie_breakdown(items, rag_matches)
            if calorie_breakdown:
                data["calorie_breakdown"] = calorie_breakdown
                breakdown_total = sum(self._to_float(row.get("calories_total"), 0.0) for row in calorie_breakdown)
                current_total = self._to_float(data.get("total_macros", {}).get("calories"), 0.0)
                if current_total <= 0:
                    data["total_macros"]["calories"] = round(breakdown_total, 1)

            # Fallback to RAG sum if synthesis is weak
            if data.get("total_macros", {}).get("calories", 0) == 0 and rag_matches:
                logger.info("[NutritionAgent] Synthesis failed macro grounding. calculating from RAG...")
                data["total_macros"]["calories"] = sum(m.get("calories", 0) for m in rag_matches)
                data["total_macros"]["protein"] = sum(m.get("protein", 0) for m in rag_matches)
                data["total_macros"]["carbs"] = sum(m.get("carbs", 0) for m in rag_matches)
                data["total_macros"]["fat"] = sum(m.get("fat", 0) for m in rag_matches)

            return json.dumps(data)

        fallback_payload = self._build_fallback_payload(vision_info, rag_matches, items)
        return json.dumps(fallback_payload)
