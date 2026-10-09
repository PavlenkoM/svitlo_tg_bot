from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from utils import GridStatus

@dataclass
class ElectricityState:
    status: Optional[GridStatus]
    lastUpdateTime: Optional[datetime]