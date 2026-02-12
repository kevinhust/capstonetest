from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
import json
import logging

logging.basicConfig(level=logging.INFO)

def test_agents():
    print("\n--- Testing FitnessAgent ---")
    f_agent = FitnessAgent()
    f_res = f_agent.execute("I have a knee injury and want some cardio advice.", [])
    print(f"Fitness Output: {f_res}")
    try:
        json.loads(f_res)
        print("✅ Fitness Output is valid JSON")
    except:
        print("❌ Fitness Output is NOT valid JSON")

    print("\n--- Testing NutritionAgent ---")
    n_agent = NutritionAgent()
    # Mocking a task (no image for this simple test)
    n_res = n_agent.execute("Tell me about chicken breast nutrition.", [])
    print(f"Nutrition Output: {n_res}")
    try:
        json.loads(n_res)
        print("✅ Nutrition Output is valid JSON")
    except:
        print("❌ Nutrition Output is NOT valid JSON")

if __name__ == "__main__":
    test_agents()
