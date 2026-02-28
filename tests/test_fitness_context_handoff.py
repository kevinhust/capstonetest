"""Regression tests for fitness orchestration and context handoff."""

import json
import os
from unittest.mock import MagicMock, patch

from agents.fitness.fitness_agent import FitnessAgent
from discord_bot.router import build_delegations
from swarm import HealthSwarm


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"})
@patch("src.agents.base_agent.BaseAgent.execute")
def test_fitness_agent_extracts_calories_from_nutrition_json(mock_execute):
    """Fitness agent should parse calories from nutrition JSON handoff."""
    mock_execute.return_value = json.dumps(
        {
            "summary": "ok",
            "recommendations": [],
            "safety_warnings": [],
            "avoid": [],
        }
    )

    agent = FitnessAgent()
    context = [
        {
            "type": "user_profile",
            "content": {
                "age": 30,
                "height": 178,
                "weight": 80,
                "conditions": ["Knee Injury"],
            },
        },
        {
            "from": "nutrition",
            "type": "nutrition_summary",
            "content": json.dumps({"total_macros": {"calories": 1200}}),
        },
    ]

    _ = agent.execute("What should I do now?", context=context)

    called_prompt = mock_execute.call_args[0][0]
    assert "Surplus Detected (1200 kcal meal)" in called_prompt
    assert "Conditions: ['Knee Injury']" in called_prompt


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"})
def test_swarm_build_context_includes_profile_and_nutrition_summary():
    """Swarm context bus should include profile payload and explicit nutrition handoff."""
    swarm = HealthSwarm(verbose=False)
    context = swarm._build_agent_context(
        agent_name="fitness",
        image_path=None,
        user_context={"age": 29, "weight": 75},
        previous_outputs=[{"agent": "nutrition", "result": "{\"ok\": true}", "error": False}],
    )

    assert any(msg.get("type") == "user_context" for msg in context)
    assert any(msg.get("type") == "user_profile" for msg in context)
    assert any(msg.get("type") == "nutrition_summary" for msg in context)


def test_router_build_delegations_uses_coordinator_for_planning():
    """Discord router should delegate workflow planning to coordinator."""
    coordinator = MagicMock()
    coordinator.analyze_and_delegate.return_value = [
        {"agent": "nutrition", "task": "Analyze this meal"}
    ]

    delegations = build_delegations(coordinator, "I ate pasta", has_image=True)

    coordinator.analyze_and_delegate.assert_called_once_with("I ate pasta [image attached]")
    assert len(delegations) == 1
    assert delegations[0].agent == "nutrition"
