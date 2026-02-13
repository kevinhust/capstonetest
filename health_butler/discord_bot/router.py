from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.coordinator.coordinator_agent import CoordinatorAgent
from health_butler.data.user_profiles import UserProfile


@dataclass(frozen=True)
class Delegation:
    agent: str  # "nutrition" | "fitness"
    task: str


def build_delegations(
    coordinator: CoordinatorAgent,
    user_text: str,
    *,
    has_image: bool,
) -> List[Delegation]:
    """
    Build delegation plan through Coordinator as the single orchestrator.

    Thin interface rule:
    - Router only forwards the message + image hint.
    - Coordinator owns all workflow policy and chaining logic.
    """
    text = (user_text or "").strip()
    planning_input = f"{text} [image attached]" if has_image else text

    raw = coordinator.analyze_and_delegate(planning_input)
    return [Delegation(agent=d["agent"], task=d["task"]) for d in raw]


def run_delegations(
    *,
    nutrition_agent: NutritionAgent,
    fitness_agent: FitnessAgent,
    delegations: Sequence[Delegation],
    user_profile: Optional[UserProfile],
    image_path: Optional[Path],
) -> Tuple[str, Dict[str, str]]:
    """
    Execute delegations and return:
    - final combined response string
    - a dict of per-agent raw responses
    """
    responses: Dict[str, str] = {}
    nutrition_response: Optional[str] = None

    for delegation in delegations:
        if delegation.agent == "nutrition":
            ctx: List[Dict] = []
            if image_path:
                ctx.append({"type": "image_path", "content": str(image_path)})
            nutrition_response = nutrition_agent.execute(delegation.task, context=ctx)
            responses["nutrition"] = nutrition_response
            continue

        if delegation.agent == "fitness":
            # Require onboarding for fitness personalization
            if user_profile is None:
                responses["fitness"] = (
                    "I can help with fitness advice, but you need to onboard first.\n"
                    "Run `/onboard` to set up your profile (age/weight/limitations/equipment)."
                )
                continue

            profile_payload = user_profile.to_dict()
            ctx2: List[Dict] = [
                {"type": "user_profile", "content": profile_payload},
                {"type": "user_context", "content": profile_payload},
            ]
            if nutrition_response:
                # Explicit nutrition -> fitness handoff (critical for your demo)
                ctx2.append(
                    {
                        "from": "nutrition",
                        "type": "nutrition_summary",
                        "content": nutrition_response,
                    }
                )
            fitness_response = fitness_agent.execute(delegation.task, context=ctx2)
            responses["fitness"] = fitness_response
            continue

        responses[delegation.agent] = f"Unknown agent: {delegation.agent}"

    # Combine output
    parts: List[str] = []
    if "nutrition" in responses:
        parts.append("**Nutrition**\n" + responses["nutrition"])
    if "fitness" in responses:
        parts.append("**Fitness**\n" + responses["fitness"])
    if not parts:
        parts.append("No response generated.")

    return "\n\n".join(parts), responses


class AgentRouter:
    """Single-entry router for Discord transport.

    The transport layer remains thin and delegates all planning to Coordinator.
    """

    def __init__(self) -> None:
        self.coordinator = CoordinatorAgent()
        self.nutrition_agent = NutritionAgent()
        self.fitness_agent = FitnessAgent()

    async def route_message(
        self,
        content: str,
        attachments: list,
        user_profile: Optional[UserProfile],
    ) -> str:
        has_image = bool(attachments)
        image_path: Optional[Path] = None
        if has_image:
            image_path = Path(getattr(attachments[0], "path", "")) if getattr(attachments[0], "path", None) else None

        delegations = build_delegations(self.coordinator, content, has_image=has_image)
        response, _ = run_delegations(
            nutrition_agent=self.nutrition_agent,
            fitness_agent=self.fitness_agent,
            delegations=delegations,
            user_profile=user_profile,
            image_path=image_path,
        )
        return response

