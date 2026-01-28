from dataclasses import dataclass
from datetime import datetime

@dataclass
class ElectricityState:
    isOn: bool
    lastUpdateTime: datetime