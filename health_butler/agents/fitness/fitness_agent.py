from typing import Optional, List, Dict, Any
import logging
import json
from src.agents.base_agent import BaseAgent
from health_butler.data_rag.enhanced_rag_tool import EnhancedRagTool

logger = logging.getLogger(__name__)

class FitnessAgent(BaseAgent):
    """
    Specialist agent for providing exercise and wellness advice.
    
    Safety-First Evolution (Phase 5):
    - Real-time Context: Uses actual user profile and daily calorie status.
    - Safety RAG: Filters exercises based on user's health conditions.
    - Dynamic Prompting: Adjusts tone and intensity based on calorie balance (Surplus/Deficit).
    """
    
    def __init__(self):
        super().__init__(
            role="fitness",
            system_prompt="""You are an expert Fitness Coach and Wellness Assistant.

Your responsibilities:
1. Suggest exercises that are SAFE and appropriate for the user's specific health conditions.
2. Adjust the intensity of recommendations based on the user's current calorie balance (Surplus vs Deficit).
3. Motivate the user to stay active while strictly respecting mechanical and health restrictions.
4. Provide clear, actionable activity suggestions (e.g., "Walking for 20 mins").

SAFETY POLICY:
- If a user has a condition (e.g., Knee Injury), NEVER suggest high-impact movements like jumping or running.
- Prioritize the "Safe Exercises" provided in the context.
- Always include a short safety warning if a health condition is present.
            """
        )
        self.rag_tool = EnhancedRagTool()

    def _calculate_bmi(self, profile: Dict[str, Any]) -> float:
        """Helper to calculate BMI from profile data."""
        try:
            height_m = float(profile.get('height', 170)) / 100
            weight_kg = float(profile.get('weight', 70))
            return round(weight_kg / (height_m * height_m), 1)
        except:
            return 22.0

    def _calculate_bmr(self, profile: Dict[str, Any]) -> float:
        """Calculate BMR using Mifflin-St Jeor Equation."""
        try:
            weight = float(profile.get('weight', 70))
            height = float(profile.get('height', 170))
            age = float(profile.get('age', 30))
            gender = profile.get('gender', 'Male').lower()
            
            bmr = (10 * weight) + (6.25 * height) - (5 * age)
            if 'female' in gender:
                bmr -= 161
            else:
                bmr += 5
            
            # Map activity level to factor
            activity_map = {
                "sedentary": 1.2,
                "lightly active": 1.375,
                "moderately active": 1.55,
                "very active": 1.725,
                "extra active": 1.9
            }
            factor = activity_map.get(profile.get('activity', '').lower(), 1.2)
            return bmr * factor
        except:
            return 2000.0

    def _determine_calorie_status(self, bmr: float, nutrition_info: str) -> str:
        """Extract calorie count from nutrition info and compare to BMR."""
        if not nutrition_info:
            return "Maintenance (No nutrition data)"
        
        # Simple extraction logic (look for patterns like "Total Calories: 500 kcal")
        import re
        match = re.search(r"Total Calories:\s*(\d+)", nutrition_info)
        if match:
            intake = int(match.group(1))
            # If intake is significant (> 40% of daily BMR in one meal), consider it a surplus-driving meal
            if intake > (bmr * 0.4):
                return f"Surplus Detected ({intake} kcal meal)"
            elif intake < (bmr * 0.15):
                return f"Deficit/Light Meal ({intake} kcal)"
        
        return "Maintenance/Balanced"

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute fitness advice task with dynamic context and safety filtering.
        """
        logger.info("[FitnessAgent] Analyzing task: %s", task)
        
        # 1. Extract Context
        user_profile = {}
        health_conditions = []
        nutrition_info = ""

        if context:
            for msg in context:
                if msg.get("type") == "user_context":
                    try:
                        content = msg.get("content", "{}")
                        if isinstance(content, str):
                            content = content.replace("'", '"')
                            user_profile = json.loads(content)
                        else:
                            user_profile = content
                        
                        health_conditions = user_profile.get("conditions", [])
                    except Exception as e:
                        logger.warning(f"[FitnessAgent] Failed to parse user_context: {e}")
                
                elif msg.get("from") == "nutrition":
                    nutrition_info = msg.get("content", "")
        
        # 2. Get Safe Recommendations from RAG
        rag_data = self.rag_tool.get_safe_recommendations(task, health_conditions)
        safe_ex_list = [f"- {e['name']}: {e.get('description', '')}" for e in rag_data['safe_exercises']]
        warnings = rag_data['safety_warnings']
        
        # 3. Dynamic Calculation (Diagram 2: CalorieCalc)
        bmr = self._calculate_bmr(user_profile)
        calorie_status = self._determine_calorie_status(bmr, nutrition_info)
        
        # 4. Build Dynamic Prompt Supplement
        bmi = self._calculate_bmi(user_profile)
        name = user_profile.get('name', 'User')
        
        dynamic_context = f"""
### USER PROFILE
- Name: {name}
- BMI: {bmi}
- Daily Maintenance (BMR x Activity): {round(bmr)} kcal
- Health Conditions: {', '.join(health_conditions) if health_conditions else 'None'}
- Primary Goal: {user_profile.get('goal', 'General Health')}

### REAL-TIME CONTEXT
- Recent Nutrition Data: {nutrition_info if nutrition_info else 'N/A'}
- Calorie Balance Analysis: {calorie_status}

### SAFETY-FILTERED KNOWLEDGE (RAG)
- Recommended SAFE Exercises:
{chr(10).join(safe_ex_list) if safe_ex_list else '- Walking (general low-impact)'}

- ⚠️ SAFETY WARNINGS:
{chr(10).join(['- ' + w for w in warnings]) if warnings else '- No specific mechanical restrictions detected.'}
"""
        
        full_task = f"{task}\n\nCONTEXTUAL DATA:\n{dynamic_context}\n\nBased on the above, provide personalized and safe advice."
        
        return super().execute(full_task, context)
