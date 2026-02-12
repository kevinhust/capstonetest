"""Supabase Profile Database Module for Health Butler.

Provides persistent storage for:
- User Profiles (profiles table)
- Daily Logs (daily_logs table)
- Chat Messages (chat_messages table)
"""

import os
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class ProfileDB:
    """Supabase database client for user profile persistence."""

    def __init__(self):
        """Initialize Supabase client from environment variables."""
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = os.getenv("SUPABASE_KEY", "")

        if not self.url or not self.key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
            )

        self.client: Client = create_client(self.url, self.key)

    # ============================================
    # Profile Operations
    # ============================================

    def get_profile(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by Discord user ID.

        Discord users are stored with their Discord ID as the profile UUID.
        For demo mode, we use Discord ID directly as the UUID.
        """
        # Note: In production, you'd have a discord_user_id column
        # For now, we'll query profiles directly (assuming auth.users.id = discord_user_id)
        response = self.client.table("profiles").select("*").eq("id", discord_user_id).execute()

        if response.data:
            return response.data[0]
        return None

    def create_profile(
        self,
        discord_user_id: str,
        full_name: str,
        age: int,
        gender: str,
        height_cm: float,
        weight_kg: float,
        goal: str,
        conditions: List[str],
        activity: str,
        diet: List[str]
    ) -> Dict[str, Any]:
        """Create a new user profile.

        Args:
            discord_user_id: Discord user ID (used as UUID)
            full_name: User's full name
            age: User's age
            gender: User's gender
            height_cm: Height in centimeters
            weight_kg: Weight in kilograms
            goal: Health goal (Lose Weight, Maintain, Gain Muscle)
            conditions: List of health conditions
            activity: Activity level
            diet: List of dietary preferences

        Returns:
            Created profile data
        """
        restrictions_str = ", ".join(conditions) if conditions and "None" not in conditions else None

        profile_data = {
            "id": discord_user_id,  # Using Discord ID as UUID for demo
            "full_name": full_name,
            "age": age,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "goal": goal,
            "restrictions": restrictions_str
        }

        response = self.client.table("profiles").insert(profile_data).execute()
        return response.data[0] if response.data else None

    def update_profile(
        self,
        discord_user_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update user profile fields.

        Args:
            discord_user_id: Discord user ID
            **updates: Fields to update (full_name, age, weight_kg, etc.)

        Returns:
            Updated profile data
        """
        response = self.client.table("profiles").update(updates).eq("id", discord_user_id).execute()
        return response.data[0] if response.data else None

    # ============================================
    # Daily Logs Operations
    # ============================================

    def create_daily_log(
        self,
        discord_user_id: str,
        log_date: date,
        calories_intake: int = 0,
        protein_g: int = 0,
        steps_count: int = 0
    ) -> Dict[str, Any]:
        """Create or update a daily log entry."""
        log_data = {
            "user_id": discord_user_id,
            "date": log_date.isoformat(),
            "calories_intake": calories_intake,
            "protein_g": protein_g,
            "steps_count": steps_count
        }

        response = self.client.table("daily_logs").insert(log_data).execute()
        return response.data[0] if response.data else None

    def get_daily_logs(self, discord_user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent daily logs for a user."""
        response = self.client.table("daily_logs").select("*").eq("user_id", discord_user_id).order("date", desc=True).limit(days).execute()
        return response.data

    # ============================================
    # Chat Messages Operations
    # ============================================

    def save_message(self, discord_user_id: str, role: str, content: str) -> Dict[str, Any]:
        """Save a chat message."""
        message_data = {
            "user_id": discord_user_id,
            "role": role,
            "content": content
        }

        response = self.client.table("chat_messages").insert(message_data).execute()
        return response.data[0] if response.data else None

    # ============================================
    # Meal Operations
    # ============================================

    def create_meal(
        self,
        discord_user_id: str,
        dish_name: str,
        calories: int = 0,
        protein_g: int = 0,
        carbs_g: int = 0,
        fat_g: int = 0,
        confidence_score: float = 0.0
    ) -> Dict[str, Any]:
        """Create a meal record."""
        meal_data = {
            "user_id": discord_user_id,
            "dish_name": dish_name,
            "calories": calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "confidence_score": confidence_score
        }
        
        response = self.client.table("meals").insert(meal_data).execute()
        return response.data[0] if response.data else None

    def get_meals(self, discord_user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent meals for a user."""
        response = self.client.table("meals").select("*").eq("user_id", discord_user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data

    def get_today_stats(self, discord_user_id: str) -> Dict[str, Any]:
        """Aggregate calories and meal count for the current day."""
        # Get UTC today start
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        response = self.client.table("meals").select("calories", "protein_g", "carbs_g", "fat_g")\
            .eq("user_id", discord_user_id)\
            .gte("created_at", today_start)\
            .execute()
        
        meals = response.data
        stats = {
            "meal_count": len(meals),
            "total_calories": sum(m.get("calories", 0) for m in meals if m.get("calories")),
            "total_protein": sum(m.get("protein_g", 0) for m in meals if m.get("protein_g")),
            "total_carbs": sum(m.get("carbs_g", 0) for m in meals if m.get("carbs_g")),
            "total_fat": sum(m.get("fat_g", 0) for m in meals if m.get("fat_g"))
        }
        return stats

    def get_chat_history(self, discord_user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chat messages for a user."""
        response = self.client.table("chat_messages").select("*").eq("user_id", discord_user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data


# Singleton instance for app-wide use
_db_instance: Optional[ProfileDB] = None


def get_profile_db() -> ProfileDB:
    """Get or create singleton ProfileDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProfileDB()
    return _db_instance
