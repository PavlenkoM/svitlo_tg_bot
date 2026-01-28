from datetime import datetime, timedelta
import asyncio
from typing import Optional
from config import config
from utils import styler, networkService
from state import stateService


class SvitloService():
    def __init__(self):
        pass

    async def checkStatus(self, ipAddress: str) -> bool:
        result = await networkService.ping(ipAddress)

        self.updateSvitloState(result)
        self.printElectricityState()

        return result
    
    
    async def runStatusChecksByTime(self, ipAddress: str, intervalSeconds: int, durationHours: Optional[int] = None) -> None:
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
                await svitloService.checkStatus(ipAddress)
                checkDuration = (datetime.now() - checkStartTime).total_seconds()
                
                print(f"Check completed in {checkDuration:.1f}s")
                
                # Calculate next check time and wait
                nextCheckTime = currentTime + timedelta(seconds=intervalSeconds)
                remainingTime = intervalSeconds - checkDuration
                
                if remainingTime > 0:
                    print(f"Next check at {nextCheckTime.strftime('%H:%M:%S')} (waiting {remainingTime/60:.1f} minutes)")
                    await asyncio.sleep(remainingTime)
                else:
                    print(f"Check took longer than interval. Starting next check immediately.")
                    
        except KeyboardInterrupt:
            print(f"\nStatus checking stopped by user at {datetime.now().strftime('%H:%M:%S')}")

    def updateSvitloState(self, isOn: bool) -> None:
        currentState = stateService.getElectricityState()
        
        if currentState.isOn == isOn:
            return  # No change in state

        styler.info(f"State change: electricity status from {currentState.isOn} to {isOn}")
        stateService.setElectricityState(isOn)


    def printElectricityState(self) -> None:
        icon = stateService.getStatusIcon()

        if stateService.isElectricityOn():
            styler.success(icon + " Electricity is ON")
        else:
            styler.error(icon + " Electricity is OFF")


svitloService = SvitloService()
