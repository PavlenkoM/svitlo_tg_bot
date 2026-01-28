#!/usr/bin/env python3
from typing import Optional
import asyncio
from config import config
from svitloService import svitloService

async def main():
    intervalSeconds: Optional[int] = config.get('timeinterval-to-check', 30)
    ipAddress: str = config['ip-address']
    
    await svitloService.runStatusChecksByTime(ipAddress, intervalSeconds)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
