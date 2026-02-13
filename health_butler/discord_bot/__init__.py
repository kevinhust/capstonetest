"""Personal Health Butler Discord Bot"""

__all__ = ["HealthButlerDiscordBot"]


def __getattr__(name: str):
	if name == "HealthButlerDiscordBot":
		from health_butler.discord_bot.bot import HealthButlerDiscordBot

		return HealthButlerDiscordBot
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
