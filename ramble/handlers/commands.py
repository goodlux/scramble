import logging
from typing import Optional
from rich.table import Table
from rich.panel import Panel
from ..ui.console import console, logger
from ..ui import panels
from ..handlers import debug

class CommandHandler:
    def __init__(self, cli):
        self.cli = cli

    def handle_command(self, cmd: str) -> None:
        """Handle CLI commands."""
        try:
            parts = cmd.strip().split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            commands = {
                ('h', 'help'): lambda: panels.show_help(),
                ('s', 'stats'): lambda: panels.show_stats(self.cli),
                ('c', 'contexts'): lambda: panels.show_contexts(self.cli.store),
                ('a', 'analysis'): lambda: panels.show_compression_analysis(self.cli),
                'dates': lambda: debug.show_context_dates(self.cli),
                'd': lambda: debug.toggle_debug(command),
                'sim': lambda: self.handle_sim_command(args),
                'inspect': lambda: debug.inspect_contexts(self.cli, args),
                'test': lambda: self.handle_test_command(args)
            }

            for cmd_keys, cmd_func in commands.items():
                if (isinstance(cmd_keys, tuple) and command in cmd_keys) or command == cmd_keys:
                    cmd_func()
                    return

            console.print("[yellow]Unknown command. Type :h for help.[/yellow]")

        except Exception as e:
            logger.error(f"Error handling command '{cmd}': {e}")
            console.print("[red]Failed to execute command[/red]")

    def handle_sim_command(self, args: str):
        """Handle similarity command."""
        if not args:
            console.print("[yellow]Usage: :sim <query text>[/yellow]")
        else:
            panels.show_similarity_debug(self.cli, args)

    def handle_test_command(self, args: str):
        """Handle test command."""
        if not args:
            console.print("[yellow]Usage: :test <message>[/yellow]")
        else:
            debug.show_context_selection(self.cli, args)