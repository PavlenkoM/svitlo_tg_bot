from datetime import datetime
from typing import Optional


class Colors:
    """ANSI color codes for terminal output styling"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class Icons:
    """Icons for different message types"""
    SUCCESS = '✅'
    ERROR = '❌'
    WARNING = '⚠️'
    INFO = 'ℹ️'
    LOADING = '🔄'
    PING = '🔍'
    POWER = '⚡'
    NETWORK = '🌐'
    BOT = '🤖'
    CHECK = '✓'
    CROSS = '✗'


class PrintStyler:
    """Utility service for styled console output with colors and icons"""
    
    def __init__(self, enableColors: bool = True, enableIcons: bool = True):
        """
        Initialize the print styler
        
        Args:
            enableColors (bool): Enable/disable color output
            enableIcons (bool): Enable/disable icon output
        """
        self.enableColors = enableColors
        self.enableIcons = enableIcons
    
    def _applyColor(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.enableColors:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def _addIcon(self, icon: str, text: str) -> str:
        """Add icon to text if icons are enabled"""
        if not self.enableIcons:
            return text
        return f"{icon} {text}"
    
    def success(self, message: str, withTimestamp: bool = False) -> None:
        """Print success message with green color and check icon"""
        text = self._addIcon(Icons.SUCCESS, message)
        text = self._applyColor(text, Colors.GREEN)
        if withTimestamp:
            text = self._addTimestamp(text)
        print(text)
    
    def error(self, message: str, withTimestamp: bool = False) -> None:
        """Print error message with red color and error icon"""
        text = self._addIcon(Icons.ERROR, message)
        text = self._applyColor(text, Colors.RED)
        if withTimestamp:
            text = self._addTimestamp(text)
        print(text)
    
    def warning(self, message: str, withTimestamp: bool = False) -> None:
        """Print warning message with yellow color and warning icon"""
        text = self._addIcon(Icons.WARNING, message)
        text = self._applyColor(text, Colors.YELLOW)
        if withTimestamp:
            text = self._addTimestamp(text)
        print(text)
    
    def info(self, message: str, withTimestamp: bool = False) -> None:
        """Print info message with blue color and info icon"""
        text = self._addIcon(Icons.INFO, message)
        text = self._applyColor(text, Colors.BLUE)
        if withTimestamp:
            text = self._addTimestamp(text)
        print(text)
    
    def loading(self, message: str) -> None:
        """Print loading message with cyan color and loading icon"""
        text = self._addIcon(Icons.LOADING, message)
        text = self._applyColor(text, Colors.CYAN)
        print(text)
    
    def ping(self, message: str) -> None:
        """Print ping-related message with cyan color and ping icon"""
        text = self._addIcon(Icons.PING, message)
        text = self._applyColor(text, Colors.CYAN)
        print(text)
    
    def power(self, message: str, isOn: bool = True) -> None:
        """Print power-related message with appropriate color"""
        text = self._addIcon(Icons.POWER, message)
        color = Colors.GREEN if isOn else Colors.RED
        text = self._applyColor(text, color)
        print(text)
    
    def network(self, message: str, isConnected: bool = True) -> None:
        """Print network-related message with appropriate color"""
        text = self._addIcon(Icons.NETWORK, message)
        color = Colors.GREEN if isConnected else Colors.RED
        text = self._applyColor(text, color)
        print(text)
    
    def bot(self, message: str) -> None:
        """Print bot-related message with purple color and bot icon"""
        text = self._addIcon(Icons.BOT, message)
        text = self._applyColor(text, Colors.PURPLE)
        print(text)
    
    def custom(self, message: str, color: str = Colors.WHITE, icon: Optional[str] = None) -> None:
        """Print custom message with specified color and icon"""
        text = message
        if icon:
            text = self._addIcon(icon, text)
        text = self._applyColor(text, color)
        print(text)
    
    def log(self, level: str, message: str) -> None:
        """Print log-style message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        levelColors = {
            'DEBUG': Colors.DIM,
            'INFO': Colors.BLUE,
            'WARNING': Colors.YELLOW,
            'ERROR': Colors.RED,
            'SUCCESS': Colors.GREEN
        }
        
        levelIcons = {
            'DEBUG': '🐛',
            'INFO': Icons.INFO,
            'WARNING': Icons.WARNING,
            'ERROR': Icons.ERROR,
            'SUCCESS': Icons.SUCCESS
        }
        
        color = levelColors.get(level.upper(), Colors.WHITE)
        icon = levelIcons.get(level.upper(), '•')
        
        text = f"[{timestamp}] {level.upper()}: {message}"
        if self.enableIcons:
            text = f"{icon} {text}"
        text = self._applyColor(text, color)
        print(text)
    
    def _addTimestamp(self, text: str) -> str:
        """Add timestamp to text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] {text}"
    
    def printBox(self, message: str, color: str = Colors.WHITE) -> None:
        """Print message in a box"""
        border = "─" * (len(message) + 2)
        boxTop = f"┌{border}┐"
        boxMiddle = f"│ {message} │"
        boxBottom = f"└{border}┘"
        
        if self.enableColors:
            boxTop = self._applyColor(boxTop, color)
            boxMiddle = self._applyColor(boxMiddle, color)
            boxBottom = self._applyColor(boxBottom, color)
        
        print(boxTop)
        print(boxMiddle)
        print(boxBottom)
    
    def printSeparator(self, character: str = "─", length: int = 50, color: str = Colors.DIM) -> None:
        """Print a separator line"""
        separator = character * length
        text = self._applyColor(separator, color)
        print(text)


# Create a global instance for easy usage
styler = PrintStyler()