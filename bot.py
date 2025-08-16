import os
import asyncio
import signal
import discord
from discord.ext import commands
from config import load_config

# Set up bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')

class SMWSBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            application_id=int(os.getenv('APPLICATION_ID'))  # Add this if available
        )
        self.initial_extensions = ['cogs.brand_commands']

    async def setup_hook(self):
        """Called when the bot is first setting up"""
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                print(f"Loaded extension: {extension}")
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}")

        # Sync commands with Discord (globally)
        try:
            print("Syncing commands globally...")
            commands = await self.tree.sync()
            print(f"Successfully registered {len(commands)} commands globally")
            for cmd in commands:
                print(f"- /{cmd.name}: {cmd.description}")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def close(self):
        """Properly close the bot and cleanup resources"""
        print("Bot is shutting down...")
        try:
            # Close all cogs properly
            for cog_name in list(self.cogs.keys()):
                await self.remove_cog(cog_name)
            
            # Call parent close method
            await super().close()
            print("Bot closed successfully")
        except Exception as e:
            print(f"Error during bot shutdown: {e}")

bot = SMWSBot()

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name} (ID: {bot.user.id})')

    # Generate invite link with proper scopes and permissions
    permissions = discord.Permissions(
        send_messages=True,
        embed_links=True,
        use_external_emojis=True,
        add_reactions=True,
        attach_files=True
    )
    invite_link = (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={bot.user.id}"
        f"&permissions={permissions.value}"
        f"&scope=bot+applications.commands"
    )
    print(f"\nInvite bot using this link:\n{invite_link}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    print(f"Command error: {error}")
    if isinstance(error, commands.errors.CommandNotFound):
        return
    await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_guild_join(guild):
    """Log when the bot joins a new server"""
    print(f"Joined new server: {guild.name} (ID: {guild.id})")
    try:
        # Sync commands for the new guild
        await bot.tree.sync()
        print(f"Synced commands for {guild.name}")
    except Exception as e:
        print(f"Error syncing commands for {guild.name}: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    logger.debug(f"Received message: {message.content}")  # Debug log

    # Get the actual prefix (bot.command_prefix might be a callable)
    prefixes = await bot.get_prefix(message)
    if isinstance(prefixes, str):
        prefixes = (prefixes,)

    # If message starts with any valid prefix, process commands
    if any(message.content.startswith(prefix) for prefix in prefixes):
        await bot.process_commands(message)
    else:
        return  # Avoid unintentional interference

async def run_bot_with_retry():
    """Run the bot with exponential backoff on rate limit errors"""
    max_retries = 3
    base_delay = 300  # 5 minutes
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to Discord (attempt {attempt + 1}/{max_retries})")
            await bot.start(os.getenv('DISCORD_TOKEN'))
            break  # If successful, break out of retry loop
            
        except discord.HTTPException as e:
            if '429' in str(e) or 'rate limit' in str(e).lower():
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited! Waiting {delay} seconds before retry...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print("Max retries reached. Rate limit persists.")
                    raise
            else:
                # For other HTTP exceptions, don't retry immediately
                print(f"HTTP Exception: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay
                    print(f"Waiting {delay} seconds before retry...")
                    await asyncio.sleep(delay)
                else:
                    raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise
        finally:
            # Ensure bot is properly closed after each attempt
            if not bot.is_closed():
                await bot.close()
                # Wait a bit after closing before next attempt
                if attempt < max_retries - 1:
                    await asyncio.sleep(30)

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"Received signal {signum}, shutting down...")
    asyncio.create_task(shutdown())

async def shutdown():
    """Graceful shutdown procedure"""
    print("Shutting down bot...")
    if not bot.is_closed():
        await bot.close()
    
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)

def main():
    # Set up signal handlers for graceful shutdown
    if os.name != 'nt':  # Not Windows
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
    
    # Run Discord bot with retry logic
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If there's already a running event loop, create a task
            task = loop.create_task(run_bot_with_retry())
        else:
            asyncio.run(run_bot_with_retry())
    except KeyboardInterrupt:
        print("Bot shutdown requested")
        # Run shutdown procedure
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(shutdown())
            else:
                asyncio.run(shutdown())
        except:
            pass
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Bot has been shut down")

if __name__ == '__main__':
    main()