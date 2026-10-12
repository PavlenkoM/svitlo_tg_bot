#!/usr/bin/env python3
from typing import Optional
import asyncio
from config import config
from svitloService import svitloService
from tgService import tgService
from homekitService import homekitService
from utils import styler

async def main() -> None:
    intervalSeconds: Optional[int] = config.get('timeinterval-to-check', 30)
    tgToken = config['telegram-token']

    tgService.setStatusProvider(svitloService.getStatusReport)

    # Optional: show the grid state in the Apple Home app. Telegram keeps working if HomeKit fails
    homekitConfig = config.get('homekit')
    if homekitConfig is not None:
        try:
            await homekitService.start(homekitConfig or {})
        except Exception as e:
            styler.error(f"Failed to start HomeKit: {e!r}")

    # Create tasks for both services to run concurrently
    bot_task = asyncio.create_task(tgService.startPolling(tgToken))
    status_task = asyncio.create_task(svitloService.runStatusChecksByTime(intervalSeconds))
    
    # Run both tasks concurrently
    try:
        await asyncio.gather(bot_task, status_task)
    except KeyboardInterrupt:
        print("\nShutting down...")
        bot_task.cancel()
        status_task.cancel()
    finally:
        await homekitService.stop()

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
