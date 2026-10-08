from datetime import datetime, timedelta
import asyncio
from typing import Optional
from config import config
import state
from utils import styler, networkService, deyeService
from state import stateService
from tgService import tgService

# Import the telegram service (avoid circular import by importing when needed)
_tg_service = None


class SvitloService():
    def __init__(self):
        pass

    def setTelegramService(self, tg_service):
        """Set the telegram service for sending notifications"""
        global _tg_service
        _tg_service = tg_service

    async def checkStatus(self) -> Optional[bool]:
        checkMethod = config.get('check-method', 'ping')

        if checkMethod == 'deye-local':
            result = await deyeService.isGridOn()
        else:
            result = await networkService.ping(config['ip-address'])

        if result is None:
            styler.warning("Electricity status is unknown. Keeping the previous state.")
            return None

        await self.updateSvitloState(isOn=result)

        return result


    async def runStatusChecksByTime(self, intervalSeconds: int, durationHours: Optional[int] = None) -> None:
        """
        Run checkStatus at time intervals
        
        Args:
            intervalSeconds: Time between checks in seconds (default: 30)
            durationHours: Total duration in hours (None for infinite)
        """
        
        # Calculate end time if duration is specified
        endTime = None
        if durationHours:
            endTime = datetime.now() + timedelta(hours=durationHours)
            styler.info(f"Status checks will run until {endTime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            while True:
                styler.printSeparator()
                
                currentTime = datetime.now()
                
                # Check if we've reached the end time
                if endTime and currentTime >= endTime:
                    styler.info(f"\nDuration limit reached. Stopping status checks.")
                    break
                
                styler.network(f"\n--- Status Check {currentTime.strftime('%H:%M:%S')} ---")
                
                # Run the status check
                checkStartTime = datetime.now()
                await svitloService.checkStatus()
                checkDuration = (datetime.now() - checkStartTime).total_seconds()
                
                styler.info(f"Check completed in {checkDuration:.1f}s")
                
                # Calculate next check time and wait
                nextCheckTime = currentTime + timedelta(seconds=intervalSeconds)
                remainingTime = intervalSeconds - checkDuration
                
                if remainingTime > 0:
                    styler.info(f"Next check at {nextCheckTime.strftime('%H:%M:%S')} (waiting {remainingTime/60:.1f} minutes)")
                    await asyncio.sleep(remainingTime)
                else:
                    styler.info(f"Check took longer than interval. Starting next check immediately.")
                    
        except KeyboardInterrupt:
            styler.warning(f"\nStatus checking stopped by user at {datetime.now().strftime('%H:%M:%S')}")


    async def updateSvitloState(self, isOn: bool) -> None:
        currentState = stateService.getElectricityState()
        
        if currentState.isOn == isOn:
            return  # No change in state

        styler.info(f"State change: electricity status from {currentState.isOn} to {isOn}")
        stateService.setElectricityState(isOn)
        await self._sendTgNotification(isOn=isOn)


    async def _sendTgNotification(self, isOn: bool) -> None:
        """Send telegram notification about electricity state change"""
        if not tgService:
            return  # Telegram service not available

        status = stateService.getStatus()
        message = f"{status['icon']} - {status['text']}"

        try:
            await tgService.sendCustomMessage(message)
        except Exception as e:
            styler.error(f"Failed to send telegram notification: {e}")


svitloService = SvitloService()
