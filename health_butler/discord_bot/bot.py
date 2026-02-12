"""
Personal Health Butler Discord Bot

Main entry point for Discord Bot deployment on Google Cloud Run.
Integrates HealthSwarm for message processing with persistent Gateway connection.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import discord
from discord import Intents, Client
from discord.ext import commands

from health_butler.swarm import HealthSwarm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_ACTIVITY = os.getenv("DISCORD_ACTIVITY", "Helping with nutrition & fitness")

# Demo Mode State (Global)
demo_mode = False
demo_user_id = None
demo_guild_id = None
demo_onboarding_step = 0  # 0: None, 1: Gender, 2: Metrics, 3: Goal
demo_user_profile = {}


class HealthButlerDiscordBot(Client):
    """
    Discord Bot for Personal Health Butler AI.

    Features:
    - Persistent Gateway connection for Cloud Run
    - Photo upload handling (sends to Nutrition Agent)
    - Text queries (routes to Coordinator)
    - Auto-reconnect on disconnect
    - Health check endpoint for Cloud Run
    - Interactive Demo Mode with Onboarding
    """

    def __init__(self):
        # Configure intents
        intents = Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.messages = True
        intents.guilds = True

        super().__init__(intents=intents, heartbeat_timeout=120)

        # Initialize Health Swarm
        self.swarm = HealthSwarm(verbose=False)
        self.start_time = datetime.now()

        logger.info("Health Butler Discord Bot initialized")

    async def setup_hook(self):
        """
        Called when the bot is starting.
        Sets up the bot's activity and status.
        """
        logger.info("Bot setup_hook executed")

    async def _handle_demo_command(self, message: discord.Message):
        """
        Handle /demo command - Toggle demo mode on/off.
        Starts the registration flow when activating.
        """
        global demo_mode, demo_user_id, demo_guild_id, demo_onboarding_step, demo_user_profile

        if not demo_mode:
            # Start registration flow
            demo_user_id = str(message.author.id)
            demo_guild_id = str(message.guild.id)
            demo_onboarding_step = 1
            demo_user_profile = {}

            await message.channel.send(
                "🎭 **Demo Mode: Registration Started**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Welcome! Let's set up your temporary health profile.\n\n"
                "**Step 1: Gender**\n"
                "Please type your gender (e.g., Male, Female, Other):"
            )
            
            logger.info(f"🚀 Registration flow started by {message.author.display_name}")

        else:
            # Exit demo mode
            demo_mode = False
            demo_user_id = None
            demo_guild_id = None
            demo_onboarding_step = 0
            demo_user_profile = {}

            await message.channel.send(
                "🛑 **Demo Mode Deactivated**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "✨ Normal user account restored"
            )

            # Reset bot activity
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=DISCORD_ACTIVITY
                )
            )

            logger.info(f"✅ Demo mode deactivated by {message.author.display_name}")

    async def _onboard_demo_user(self, message: discord.Message):
        """Handle the interactive steps for demo user registration."""
        global demo_mode, demo_onboarding_step, demo_user_profile

        content = message.content.strip()

        if demo_onboarding_step == 1:
            # Process Gender
            demo_user_profile["gender"] = content
            demo_onboarding_step = 2
            await message.channel.send(
                "✅ Gender recorded.\n\n"
                "**Step 2: Metrics**\n"
                "Please type your Height and Weight (e.g., 180cm, 75kg):"
            )

        elif demo_onboarding_step == 2:
            # Process Metrics
            demo_user_profile["metrics"] = content
            demo_onboarding_step = 3
            await message.channel.send(
                "✅ Metrics recorded.\n\n"
                "**Step 3: Goal**\n"
                "What is your primary health goal? (e.g., Muscle gain, Weight loss):"
            )

        elif demo_onboarding_step == 3:
            # Process Goal
            demo_user_profile["goal"] = content
            demo_onboarding_step = 0
            demo_mode = True # Registration complete!

            # Final Welcome Message
            await message.channel.send(
                "🎉 **Registration Complete!**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👤 **Temporary Demo Profile Ready**\n"
                f"• Gender: `{demo_user_profile.get('gender')}`\n"
                f"• Metrics: `{demo_user_profile.get('metrics')}`\n"
                f"• Goal: `{demo_user_profile.get('goal')}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 **Demo Rules**:\n"
                "1️⃣ All responses will be tagged with `[DEMO]`\n"
                "2️⃣ Auto-exit after demo session ends\n"
                "3️⃣ Conversation history will not be saved\n"
                "4️⃣ Type `/demo` again to exit demo mode\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✨ You can now ask questions or upload food photos!"
            )

            # Update bot activity
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="[Demo Mode] " + DISCORD_ACTIVITY
                )
            )
            logger.info(f"✅ Demo registration complete for {message.author.display_name}")

    async def _handle_exit_command(self, message: discord.Message):
        """
        Handle /exit or /quit command - Only works in demo mode.

        Exits demo mode and returns to normal account.
        """
        global demo_mode, demo_user_id, demo_guild_id, demo_onboarding_step, demo_user_profile

        if not demo_mode and demo_onboarding_step == 0:
            await message.channel.send("⚠️ Currently not in Demo Mode.\nType `/demo` to enter demo mode first.")
            return

        # Exit demo mode or cancel registration
        demo_mode = False
        demo_user_id = None
        demo_guild_id = None
        demo_onboarding_step = 0
        demo_user_profile = {}

        await message.channel.send(
                "🛑 **Exited Demo Mode**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "✨ Demo account closed\n"
                f"👋 Owner: {message.author.mention}\n"
                "✨ Normal user account restored"
            )

        # Reset bot activity
        await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=DISCORD_ACTIVITY
                )
            )

        logger.info(f"✅ Demo mode exited by {message.author.display_name}")

    async def on_ready(self):
        """
        Called when the bot has successfully connected to Discord Gateway.
        """
        logger.info(f"✅ Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guild(s)")
        logger.info(f"⏱️ Uptime started at {self.start_time.isoformat()}")

    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages from Discord.

        Routes to appropriate agent based on content:
        - /demo command → Enter/exit demo mode
        - Registration flow → Process onboarding steps
        - With image attachment → Nutrition Agent (food analysis)
        - Text query → Coordinator (intent routing)
        """
        global demo_mode, demo_user_id, demo_guild_id, demo_onboarding_step

        # Ignore messages from bots (including self)
        if message.author.bot:
            return

        # Ignore DMs for MVP (guild messages only)
        if not message.guild:
            return

        # Check for /demo command
        if message.content.strip().lower() == "/demo":
            await self._handle_demo_command(message)
            return

        # Check for /exit or /quit command (works during registration too)
        content_lower = message.content.strip().lower()
        if content_lower in ("/exit", "/quit"):
            if demo_mode or demo_onboarding_step > 0:
                await self._handle_exit_command(message)
            else:
                await message.channel.send("⚠️ `/exit` command can only be used in Demo Mode.\nType `/demo` to enter demo mode first.")
            return

        # Check for onboarding state
        if demo_onboarding_step > 0 and str(message.author.id) == demo_user_id:
            await self._onboard_demo_user(message)
            return

        # In demo mode, only respond to demo user
        if demo_mode and str(message.author.id) != demo_user_id:
            return

        # Process message
        logger.info(
            f"[{message.guild.name}] #{message.channel.name} "
            f"@{message.author.display_name}: {message.content[:50]}..."
        )

        try:
            # Check for image attachments
            image_attachment = None
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    image_attachment = attachment
                    break

            # Build user context
            user_context = {
                "user_id": str(message.author.id),
                "username": message.author.display_name,
                "guild_id": str(message.guild.id),
                "channel_id": str(message.channel.id),
                "timestamp": message.created_at.isoformat()
            }

            # Process based on input type
            if image_attachment:
                await self._process_image_message(
                    message, image_attachment, user_context
                )
            else:
                await self._process_text_message(message, user_context)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.channel.send(
                f"⚠️ Sorry, I encountered an error: {str(e)}"
            )

    async def _process_image_message(
        self,
        message: discord.Message,
        attachment: discord.Attachment,
        user_context: dict
    ):
        """
        Process message with image attachment.

        Downloads image and sends to Nutrition Agent for analysis.
        """
        # Send typing indicator
        async with message.channel.typing():
            # Download image
            image_path = f"/tmp/{attachment.filename}"
            try:
                await attachment.save(image_path)
                logger.info(f"Downloaded image to {image_path}")

                # Process with Swarm
                result = self.swarm.execute(
                    user_input=f"Analyze this meal photo",
                    image_path=image_path,
                    user_context=user_context
                )

                # Add [DEMO] prefix if in demo mode
                if demo_mode:
                    result['response'] = f"[DEMO] {result['response']}"

                # Send response
                await self._send_swarmed_response(
                    message.channel, result['response']
                )

            finally:
                # Cleanup temp file
                if os.path.exists(image_path):
                    os.remove(image_path)

    async def _process_text_message(
        self,
        message: discord.Message,
        user_context: dict
    ):
        """
        Process text-only message.

        Routes through Coordinator for intent analysis.
        """
        # Send typing indicator
        async with message.channel.typing():
            # Process with Swarm
            result = self.swarm.execute(
                user_input=message.content,
                image_path=None,
                user_context=user_context
            )

            # Add [DEMO] prefix if in demo mode
            if demo_mode:
                result['response'] = f"[DEMO] {result['response']}"

            # Send response
            await self._send_swarmed_response(
                message.channel, result['response']
            )

    async def _send_swarmed_response(
        self,
        channel: discord.abc.Messageable,
        response: str
    ):
        """
        Send swarm response to Discord channel.

        Handles Discord's 2000 character limit by splitting long responses.
        """
        MAX_LENGTH = 1900  # Leave some buffer

        if len(response) <= MAX_LENGTH:
            await channel.send(response)
        else:
            # Split into chunks
            chunks = []
            current_chunk = ""

            for line in response.split('\n'):
                if len(current_chunk) + len(line) + 1 <= MAX_LENGTH:
                    current_chunk += line + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'

            if current_chunk:
                chunks.append(current_chunk.strip())

            # Send chunks
            for i, chunk in enumerate(chunks, 1):
                await channel.send(
                    f"📋 **Part {i}/{len(chunks)}**\n{chunk}"
                )
                # Small delay between chunks
                if i < len(chunks):
                    await asyncio.sleep(0.5)

    async def on_disconnect(self):
        """Handle unexpected disconnects with auto-reconnect."""
        logger.warning("⚠️ Bot disconnected from Discord Gateway")
        logger.info("🔄 Auto-reconnect is handled by discord.py library")

    async def on_resumed(self):
        """Handle successful reconnection."""
        logger.info("✅ Bot reconnected to Discord Gateway")

    def run_with_health_check(self, host: str = "0.0.0.0", port: int = 8080):
        """
        Run bot with health check server for Cloud Run.

        Cloud Run requires the container to respond on $PORT for health checks.
        Since Discord Bot uses persistent WebSocket connection,
        we run a simple HTTP server in background.

        Args:
            host: Host for health check server
            port: Port for health check (from Cloud Run $PORT)
        """
        from aiohttp import web

        async def health_check(request):
            """Simple health check endpoint."""
            uptime = datetime.now() - self.start_time
            return web.json_response({
                "status": "healthy",
                "uptime_seconds": int(uptime.total_seconds()),
                "bot_connected": self.is_ready(),
                "timestamp": datetime.now().isoformat()
            })

        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)

        # Start health check server in background
        runner = web.AppRunner(app)
        loop = asyncio.get_event_loop()

        async def start_health_server():
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            logger.info(f"🏥 Health check server listening on {host}:{port}")

        async def start_bot():
            await self.start(DISCORD_TOKEN)

        async def main():
            await asyncio.gather(
                start_health_server(),
                start_bot()
            )

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
            loop.run_until_complete(runner.cleanup())


# For backwards compatibility with old import
class HealthSwarmOrchestrator(HealthSwarm):
    """Alias for backwards compatibility."""
    pass


def main():
    """Entry point for running the bot directly."""
    bot = HealthButlerDiscordBot()

    # Get port from Cloud Run environment
    port = int(os.getenv("PORT", "8080"))

    bot.run_with_health_check(port=port)


if __name__ == "__main__":
    main()
