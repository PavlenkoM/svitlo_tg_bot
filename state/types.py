from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from utils import GridStatus

@dataclass
class ElectricityState:
    status: Optional[GridStatus]
    phaseIcons: Tuple[str, ...]  # zone icon of each phase in the last notification
    lastUpdateTime: Optional[datetime]