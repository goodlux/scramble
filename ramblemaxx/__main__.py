#!/usr/bin/env python3
import signal
from ramblemaxx.app import RambleMaxx

def handle_sigint(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\nGoodbye! 👋")
    exit(0)

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    app = RambleMaxx()
    app.run()

if __name__ == "__main__":
    main()