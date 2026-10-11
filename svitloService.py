from datetime import datetime, timedelta
import asyncio
from typing import List, Optional, Tuple
from config import config
import state
from utils import styler, deyeService, GridStatus
from state import stateService
from storage import storageService
from tgService import tgService

# Phase voltage considered good, volts (230 V ±10% is 207-253 V by EU standard)
GOOD_VOLTAGE_MIN = 220
GOOD_VOLTAGE_MAX = 250

# Import the telegram service (avoid circular import by importing when needed)
_tg_service = None


class SvitloService():
    def __init__(self):
        pass

    def setTelegramService(self, tg_service):
        """Set the telegram service for sending notifications"""
        global _tg_service
        _tg_service = tg_service

    async def checkStatus(self) -> Optional[GridStatus]:
        reading = await deyeService.checkGrid()

        if reading is None:
            styler.warning("Electricity status is unknown. Keeping the previous state.")
            return None

        status = deyeService.getGridStatus(reading)
        await self.updateSvitloState(status=status, voltages=reading.voltages)

        return status


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


    async def updateSvitloState(self, status: GridStatus, voltages: List[float]) -> None:
        currentState = stateService.getElectricityState()
        phaseIcons = tuple(self._getPhaseIcon(voltage) for voltage in voltages)

        if currentState.status != status:
            previous = currentState.status.value if currentState.status else "UNKNOWN"
            styler.info(f"State change: electricity status from {previous} to {status.value}")
        elif status is GridStatus.PARTIAL and self._getRedPhases(currentState.phaseIcons) != self._getRedPhases(phaseIcons):
            # Still PARTIAL, but a phase moved to or from 🔴 (🟢 <-> 🟡 is not worth a message)
            styler.info(f"Phase change: {''.join(currentState.phaseIcons)} to {''.join(phaseIcons)}")
        else:
            return  # No change in state

        # Chats without PARTIAL notifications see PARTIAL as ON: notify them only when ON/OFF changes
        isBasicStatusChanged = self._getBasicStatus(currentState.status) != self._getBasicStatus(status)

        stateService.setElectricityState(status, phaseIcons)

        await self._sendTgNotification(status, voltages, storageService.getAllChatIds(show_partial=True))
        if isBasicStatusChanged:
            await self._sendTgNotification(self._getBasicStatus(status), voltages, storageService.getAllChatIds(show_partial=False))


    def _getBasicStatus(self, status: Optional[GridStatus]) -> Optional[GridStatus]:
        """ON/OFF only: PARTIAL counts as ON"""
        return GridStatus.ON if status is GridStatus.PARTIAL else status


    def _getRedPhases(self, phaseIcons: Tuple[str, ...]) -> Tuple[bool, ...]:
        return tuple(icon == "🔴" for icon in phaseIcons)


    def _getPhaseIcon(self, voltage: float) -> str:
        if voltage < deyeService.getMinGridVoltage():
            return "🔴"  # No electricity on the phase
        if GOOD_VOLTAGE_MIN <= voltage <= GOOD_VOLTAGE_MAX:
            return "🟢"
        return "🟡"  # Too low or too high voltage


    async def _sendTgNotification(self, status: GridStatus, voltages: List[float], chatIds: List[int]) -> None:
        """Send telegram notification about electricity state change"""
        if not tgService or not chatIds:
            return  # Telegram service not available or nobody to notify

        phasesText = ' | '.join(f"{self._getPhaseIcon(voltage)} {voltage:.0f} V" for voltage in voltages)
        message = f"{stateService.getIconFor(status)} - {status.value}\n{phasesText}"

        try:
            await tgService.sendCustomMessage(message, chat_ids=chatIds)
        except Exception as e:
            styler.error(f"Failed to send telegram notification: {e}")


svitloService = SvitloService()
