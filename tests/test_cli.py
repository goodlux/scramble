import pytest
from click.testing import CliRunner
from scramble.cli.app import RambleCLI

def test_cli_starts():
    """Test that CLI initializes correctly"""
    app = RambleCLI()
    assert app.compressor is not None
    assert app.store is not None