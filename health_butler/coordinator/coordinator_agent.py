"""
Coordinator Agent for Health Butler AI system.

Routes user requests to appropriate specialist agents (Nutrition/Fitness)
based on keyword analysis and health context. Extends RouterAgent
with health-specific delegation logic.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from src.agents.router_agent import RouterAgent
from src.config import settings
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)

class CoordinatorAgent(RouterAgent):
    """
    Health-specific Router Agent with enhanced context management.
    
    Responsibilities:
    - Route requests to Nutrition or Fitness agents
    - Load and pass user profiles to agents
    - Chain Nutrition output to Fitness input (meal → exercise advice)
    - Maintain conversation context for goal tracking
    """
    
    def __init__(self):
        system_prompt = """You are the Coordinator Agent for the Personal Health Butler AI.
Your goal is to delegate user requests to the most appropriate health specialist.

Available specialist agents:
- nutrition: Analyzes food images or descriptions, estimates calories/macros.
- fitness: Suggests exercises, sets goals, tracks progress, learns preferences.

You MUST respond with a valid JSON planning object.
"""
        # Initialize BaseAgent directly to override Router's role
        super(CoordinatorAgent, self).__init__(role="coordinator", system_prompt=system_prompt)

    def analyze_and_delegate(self, user_task: str) -> List[Dict[str, Any]]:
        """
        Analyze task using Gemini Structured Output for 100% reliable JSON.
        """
        if not self.client:
            return self._simple_delegate(user_task)

        prompt = f"PLAN DELEGATION FOR TASK: {user_task}"
        
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=self.system_prompt + "\n\n" + prompt,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "delegations": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "agent": {"type": "STRING"},
                                        "task": {"type": "STRING"}
                                    },
                                    "required": ["agent", "task"]
                                }
                            }
                        },
                        "required": ["delegations"]
                    }
                )
            )
            
            data = response.parsed
            if isinstance(data, dict) and "delegations" in data:
                return data["delegations"]
            return self._simple_delegate(user_task)
            
        except Exception as e:
            logger.error(f"CoordinatorAgent delegation failed: {e}")
            return self._simple_delegate(user_task)

    def _simple_delegate(self, task: str) -> List[Dict[str, Any]]:
        """
        Enhanced health-specific fallback delegation with chaining support.
        """
        task_lower = task.lower()
        delegations = []
        
        # Check for goal-related keywords (fitness only)
        if any(word in task_lower for word in ['goal', 'progress', 'track', 'lose weight', 'gain muscle']):
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations
        
        # Check for exercise completion tracking
        if any(word in task_lower for word in ['completed', 'finished', 'done with']) and \
           any(word in task_lower for word in ['walk', 'run', 'swim', 'exercise', 'workout']):
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations
        
        # Check for nutrition keywords
        has_nutrition = any(word in task_lower for word in [
            'food', 'eat', 'ate', 'calorie', 'meal', 'nutrition', 
            'diet', 'lunch', 'dinner', 'breakfast', 'snack'
        ])
        
        # Check for fitness keywords
        has_fitness = any(word in task_lower for word in [
            'exercise', 'walk', 'run', 'gym', 'workout', 'fitness', 
            'steps', 'activity', 'burn calories'
        ])
        
        # Meal analysis → chain both agents
        if has_nutrition and ('ate' in task_lower or 'just ate' in task_lower or 'i ate' in task_lower):
            # First nutrition to analyze meal
            delegations.append({'agent': 'nutrition', 'task': task})
            # Then fitness to suggest exercises
            delegations.append({
                'agent': 'fitness',
                'task': 'Suggest exercises to balance this meal intake'
            })
            return delegations
        
        # Nutrition only
        if has_nutrition:
            delegations.append({'agent': 'nutrition', 'task': task})
        
        # Fitness only
        if has_fitness:
            delegations.append({'agent': 'fitness', 'task': task})
        
        # Default to nutrition if ambiguous (it's a food app typically)
        if not delegations:
            delegations.append({'agent': 'nutrition', 'task': task})
        
        return delegations
    
    def supports_chaining(self) -> bool:
        """Indicate that this coordinator supports agent chaining."""
        return True
