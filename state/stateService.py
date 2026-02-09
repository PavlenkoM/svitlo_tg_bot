from datetime import datetime
from typing import Optional
from utils import styler
from .types import ElectricityState

class StateService:
    def __init__(self):
        self._electricityState: ElectricityState = ElectricityState(isOn = None, lastUpdateTime = None)


    def getElectricityState(self) -> ElectricityState:
        return self._electricityState

 
    def setElectricityState(self, isOn: bool) -> None:
        self._electricityState.isOn = isOn
        self._electricityState.lastUpdateTime = datetime.now()


    def getStatusIcon(self) -> str:
        if self._electricityState.isOn is None:
            return "❓"  # Unknown state
        return "💡" if self._electricityState.isOn else "🌚"
    
    def getStatus(self) -> dict:
        state = self.getElectricityState()
        return {
            "isOn": state.isOn,
            "lastUpdateTime": state.lastUpdateTime,
            "icon": self.getStatusIcon(),
            "text": "ON" if state.isOn else "OFF" if state.isOn is not None else "UNKNOWN"
        }
    
    
    def isElectricityOn(self) -> Optional[bool]:
        return self._electricityState.isOn



stateService = StateService()