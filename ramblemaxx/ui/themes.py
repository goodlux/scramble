from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class MAXXTheme:
    """Theme configuration for RambleMAXX."""
    name: str
    colors: Dict[str, str]
    styles: Dict[str, Any]

# Define some MAXXED OUT themes
THEMES = {
    "default": MAXXTheme(
        name="Default MAXX",
        colors={
            "background": "#1a1b26",
            "foreground": "#c0caf5",
            "accent": "#7aa2f7",
            "error": "#f7768e",
        },
        styles={
            "chat": {"border": "rounded"},
            "code": {"border": "heavy"},
        }
    ),
    "cyber": MAXXTheme(
        name="Cyber MAXX",
        colors={
            "background": "#000000",
            "foreground": "#00ff00",
            "accent": "#ff00ff",
            "error": "#ff0000",
        },
        styles={
            "chat": {"border": "double"},
            "code": {"border": "double"},
        }
    ),
}

def get_theme(name: str = "default") -> MAXXTheme:
    """Get a theme by name."""
    return THEMES.get(name, THEMES["default"])