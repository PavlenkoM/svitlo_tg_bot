from datetime import datetime
from typing import Optional, Tuple
from utils import styler, GridStatus
from .types import ElectricityState

class StateService:
    def __init__(self):
        self._electricityState: ElectricityState = ElectricityState(status = None, phaseIcons = (), lastUpdateTime = None)


    def getElectricityState(self) -> ElectricityState:
        return self._electricityState

 
    def setElectricityState(self, status: GridStatus, phaseIcons: Tuple[str, ...]) -> None:
        self._electricityState.status = status
        self._electricityState.phaseIcons = phaseIcons
        self._electricityState.lastUpdateTime = datetime.now()


    def getStatusIcon(self) -> str:
        icons = {GridStatus.ON: "💡", GridStatus.PARTIAL: "⚠️", GridStatus.OFF: "🌚"}
        return icons.get(self._electricityState.status, "❓")  # ❓ - unknown state
    
    def getStatus(self) -> dict:
        state = self.getElectricityState()
        return {
            "status": state.status,
            "lastUpdateTime": state.lastUpdateTime,
            "icon": self.getStatusIcon(),
            "text": state.status.value if state.status else "UNKNOWN"
        }




stateService = StateService()