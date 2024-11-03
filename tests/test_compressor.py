import pytest

@pytest.fixture
def sample_dialogue_fixture():
    return (
        "Human: How does quantum entanglement work?"
        "Assistant: Quantum entanglement is a phenomenon where particles become correlated in such a way that the quantum state of each particle cannot be described independently."
    )