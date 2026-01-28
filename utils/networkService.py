import asyncio
from config import config
from utils import styler

class NetworkService:
    async def ping(self, ipAddress: str) -> bool:
        """
        Ping an IP address to check if it's reachable.
        """
        styler.ping(f'Pinging {ipAddress}...')
        packetsQuantity = config.get('svitlo', {}).get('number-of-packets', 4)
        
        try:
            result = await asyncio.create_subprocess_exec(
                'ping', '-c', str(packetsQuantity), '-W', '3', ipAddress,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await result.communicate()
            isReachable = result.returncode == 0

            if isReachable:
                styler.success(f'{ipAddress} is reachable.')
            else:
                styler.error(f'{ipAddress} is not reachable.')
            
            return isReachable
            
        except Exception as e:
            return False
        
networkService = NetworkService()
