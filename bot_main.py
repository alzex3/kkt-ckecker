import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import router
from bot.utils import FileManager
from config import get_config


def create_pidfile():
    """Create a PID file to prevent multiple instances"""
    pidfile_path = Path("bot.pid")

    if pidfile_path.exists():
        try:
            with pidfile_path.open() as f:
                old_pid = int(f.read().strip())

            # Check if process is still running
            os.kill(old_pid, 0)  # This will raise OSError if process doesn't exist
            logging.error(f"Bot is already running with PID {old_pid}")
            logging.error("Stop the existing instance first or delete bot.pid if it's stale")
            sys.exit(1)

        except (OSError, ValueError):
            # Process doesn't exist or invalid PID, remove stale pidfile
            pidfile_path.unlink()

    # Write current PID
    with pidfile_path.open("w") as f:
        f.write(str(os.getpid()))

    def cleanup_pidfile():
        pidfile_path.unlink(missing_ok=True)

    return cleanup_pidfile


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Create PID file to prevent multiple instances
    cleanup_pidfile = create_pidfile()

    try:
        config = get_config()
    except ValueError as config_error:
        logging.error(f"Configuration error: {config_error}")
        logging.error("Please create a .env file with BOT_TOKEN or set the environment variable")
        cleanup_pidfile()
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Initialize file manager
    file_manager = FileManager(config)

    # Store dependencies in dispatcher for dependency injection
    dp["config"] = config
    dp["file_manager"] = file_manager

    # Include routers
    dp.include_router(router)

    # Cleanup function
    async def cleanup():
        await file_manager.cleanup_all_files()
        await bot.session.close()

    try:
        logging.info("Starting KKT Bot...")

        # Get bot info
        bot_info = await bot.get_me()
        logging.info(f"Bot @{bot_info.username} is running")

        # Start polling
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        await cleanup()
        cleanup_pidfile()
        logging.info("Bot stopped")


if __name__ == "__main__":

    def signal_handler(signum, _):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by KeyboardInterrupt")
    except Exception as bot_error:
        logging.error(f"Failed to start bot: {bot_error}")
        sys.exit(1)
