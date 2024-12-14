from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.style import Style
from datetime import datetime
import logging

__all__ = ['console', 'logger', 'setup_logging', 'prompt_user']  # Add this line to be explicit

console = Console(stderr=True, soft_wrap=True)

# Option 1: Cyberpunk style
def get_prompt_cyberpunk():
    timestamp = datetime.now().strftime("%H:%M")
    return f"[bold blue]╭─[/bold blue][bold cyan]ramble[/bold cyan] [dim]{timestamp}[/dim]\n[bold blue]╰─[/bold blue][bold green]>[/bold green] "

# Option 2: Minimal but elegant
def get_prompt_minimal():
    timestamp = datetime.now().strftime("%H:%M")
    return f"[bold purple]⟫[/bold purple] [dim]{timestamp}[/dim] [bold purple]⟫[/bold purple] "

# Option 3: Terminal style
def get_prompt_terminal():
    timestamp = datetime.now().strftime("%H:%M")
    return f"[bold green]ramble[/bold green][dim]@{timestamp}[/dim][bold white]:[/bold white] "

# Option 4: Scroll themed (matching your project concept)
def get_prompt_scroll():
    timestamp = datetime.now().strftime("%H:%M")
    return f"[bold yellow]📜[/bold yellow] [cyan]{timestamp}[/cyan] [bold yellow]╾━>[/bold yellow] "

def prompt_user(prompt_style="scroll"):
    """Get user input with styled prompt."""
    prompt_funcs = {
        "cyberpunk": get_prompt_cyberpunk,
        "minimal": get_prompt_minimal,
        "terminal": get_prompt_terminal,
        "scroll": get_prompt_scroll
    }
    
    prompt_func = prompt_funcs.get(prompt_style, get_prompt_scroll)
    return Prompt.ask(prompt_func())

# Rest of console.py setup
def setup_logging(console: Console) -> None:
    """Configure application logging with rich handler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=False,
                show_path=False,
                markup=True
            )
        ]
    )

logger = logging.getLogger(__name__)