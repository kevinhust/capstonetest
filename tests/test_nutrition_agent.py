import sys
import os
import json
import pytest

# Add project root to python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)

pytest.importorskip("torch")

from src.agents.nutrition.nutrition_agent import NutritionAgent

def test_nutrition_agent_flow():
    print("Testing Nutrition Agent Flow...")
    
    agent = NutritionAgent()
    
    image_path = "test_meal.jpg"
    query = "Is this good for building muscle?"
    
    print(f"Input: Image='{image_path}', Query='{query}'")
    
    context = [
        {"type": "image_path", "content": image_path},
        {"type": "user_context", "content": json.dumps({"goal": "build muscle"})}
    ]
    
    result_str = agent.execute(query, context)
    
    print("\n--- Result ---")
    print(result_str)
    
    # NutritionAgent.execute returns a JSON string
    result = json.loads(result_str)
    
    # Assert actual response structure
    assert "dish_name" in result
    assert "total_macros" in result
    assert "composition_analysis" in result
    assert "health_tip" in result
    
    print("\n✅ Test Passed!")

if __name__ == "__main__":
    test_nutrition_agent_flow()
