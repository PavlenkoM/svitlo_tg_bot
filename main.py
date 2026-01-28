#!/usr/bin/env python3
from typing import Optional
import asyncio
from config import config
from svitloService import svitloService
from tgService import tgService

async def main() -> None:
    intervalSeconds: Optional[int] = config.get('timeinterval-to-check', 30)
    ipAddress: str = config['ip-address']
    tgToken = config['telegram-token']
    
    # Create tasks for both services to run concurrently
    bot_task = asyncio.create_task(tgService.startPolling(tgToken))
    status_task = asyncio.create_task(svitloService.runStatusChecksByTime(ipAddress, intervalSeconds))
    
    # Run both tasks concurrently
    try:
        await asyncio.gather(bot_task, status_task)
    except KeyboardInterrupt:
        print("\nShutting down...")
        bot_task.cancel()
        status_task.cancel()

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
