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
    
    
    def isElectricityOn(self) -> Optional[bool]:
        return self._electricityState.isOn



stateService = StateService()