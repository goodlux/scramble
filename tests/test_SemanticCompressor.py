import unittest
import numpy as np
from typing import Dict
from pathlib import Path
from datetime import datetime, timedelta

from scramble.core.context import Context  # Add this
from scramble.core.compressor import SemanticCompressor
from scramble.core.compressor import CompressionLevel

# Define store path
store_path = Path.home() / '.ramble' / 'store'

class TestSemanticCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = SemanticCompressor()
        self.store_path = Path.home() / '.ramble' / 'store'


    def test_compression_settings_with_levels(self):  # Changed function name and removed parameter
        """Test compression with different settings across all stored contexts."""
        for level in ['LOW', 'MEDIUM', 'HIGH']:
            self.compressor.set_compression_level(level)

            total_original = 0
            total_compressed = 0
            similarities = []

            def read_full_file(path: Path) -> str:
                with open(path, 'r') as f:
                    return f.read()

            for ctx_file in self.store_path.glob('*.full'):
                # Read original
                original = read_full_file(ctx_file)

                # Try compression
                compressed_context = self.compressor.compress(original)
                compressed_text = self._extract_text_content(compressed_context)

                # Measure results
                total_original += len(original)
                total_compressed += len(compressed_text)
                similarities.append(self._measure_similarity(original, compressed_text))

            results = {
                'level': level,
                'ratio': total_original / total_compressed,
                'avg_similarity': np.mean(similarities),
                'min_similarity': np.min(similarities)
            }

            print(f"\nCompression results for {level}:")
            print(f"Ratio: {results['ratio']:.2f}x")
            print(f"Average similarity: {results['avg_similarity']:.2f}")
            print(f"Minimum similarity: {results['min_similarity']:.2f}")

            # Add assertions
            self.assertGreater(results['ratio'], 1.1, f"Poor compression for {level}")
            self.assertGreater(results['avg_similarity'], 0.8, f"Poor similarity for {level}")

    def _extract_text_content(self, context: Context) -> str:
        """Helper method to extract text from context."""
        text_parts = []
        for token in context.compressed_tokens:
            if isinstance(token, dict) and 'content' in token:
                content = token['content']
                speaker = token.get('speaker', '')
                if speaker:
                    text_parts.append(f"{speaker}: {content}")
                else:
                    text_parts.append(content)
            elif isinstance(token, str):
                text_parts.append(token)
        return "\n".join(text_parts)

    def _measure_similarity(self, text1: str, text2: str) -> float:
        """Helper method to measure text similarity."""
        # For now, using simple length ratio as similarity
        # Could be enhanced with proper semantic similarity
        return min(len(text1), len(text2)) / max(len(text1), len(text2))


    def test_compression_settings(self, compression_level: Dict):

        store_path = Path("./store/full_test")
        total_original = 0
        total_compressed = 0
        similarities = []

        for ctx_file in store_path.glob('*.full'):
            # Read original
            original = read_full_file(ctx_file)

            # Try compression
            compressed = compress_with_settings(original, compression_level)

            # Measure results
            total_original += len(original)
            total_compressed += len(compressed)
            similarities.append(measure_similarity(original, compressed))

        return {
            'ratio': total_original / total_compressed,
            'avg_similarity': np.mean(similarities),
            'min_similarity': np.min(similarities)
        }

    def test_compression_effectiveness(self):

        """Test different compression levels and their effectiveness."""
        test_cases = {

            'short_conversation': """
            Human: Hi there!
            Assistant: Hello! How can I help you today?
            """,

            'medium_conversation':  """
            Human: Can you explain how neural networks work?
            Assistant: Neural networks are computational models inspired by biological brains. They consist of layers of connected nodes.
            Human: What are these layers?
            Assistant: There are typically three types of layers:
            1. Input layer - receives raw data
            2. Hidden layers - process information
            3. Output layer - produces final results
            Each layer performs specific computations and passes information forward.
            """,

            'long_technical': """
            Human: Let's discuss quantum computing in detail.
            Assistant: I'll explain quantum computing comprehensively.

            First, let's understand classical bits vs qubits:
            - Classical bits are either 0 or 1
            - Qubits can exist in superposition of states

            Key quantum computing concepts:
            1. Superposition
            2. Entanglement
            3. Quantum gates
            4. Quantum algorithms

            Let me elaborate on each of these concepts in detail...
            [Long technical explanation with specific terms repeated]

            Application areas include:
            - Cryptography
            - Drug discovery
            - Optimization
            - Machine learning

            Common quantum algorithms:
            1. Shor's algorithm
            2. Grover's algorithm
            3. VQE
            4. QAOA

            Would you like me to explain any of these in more detail?
            """,

            'repeated_patterns': """
            Human: What's the weather like today?
            Assistant: Today will be sunny with a high of 75°F and a low of 60°F.
            Human: What about tomorrow?
            Assistant: Tomorrow will be sunny with a high of 73°F and a low of 58°F.
            Human: And the day after?
            Assistant: The day after tomorrow will be sunny with a high of 72°F and a low of 59°F.
            Human: What's the general pattern?
            Assistant: We're seeing a consistent pattern of sunny days with highs in the 70s and lows around 60°F.
            Human: Any rain coming?
            Assistant: No rain in the forecast. Continuing sunny with highs in the 70s and lows around 60°F.
            Human: Perfect for the weekend?
            Assistant: Yes, the weekend will be perfect - sunny with highs in the 70s and lows around 60°F.
            """
        }

        for name, text in test_cases.items():
            for level in ['LOW', 'MEDIUM', 'HIGH']:
                with self.subTest(case=name, level=level):
                    self.compressor.set_compression_level(level)
                    context = self.compressor.compress(text)

                    # Print detailed compression stats for debugging
                    print(f"\nTesting {name} at {level}:")
                    print(f"Original length: {len(text)}")
                    print(f"Compressed length: {context.metadata['compressed_length']}")
                    print(f"Compression ratio: {context.metadata['compression_ratio']:.2f}x")
                    print(f"Semantic similarity: {context.metadata['semantic_similarity']:.2f}")

                    # Check compression metrics
                    self.assertGreater(
                        context.metadata['compression_ratio'],
                        1.1,  # Require at least 1.1x compression
                        f"Poor compression for {name} at {level}"
                    )

                    # Verify semantic preservation
                    self.assertGreater(
                        context.metadata['semantic_similarity'],
                        0.8,  # Minimum similarity threshold
                        f"Lost too much meaning in {name} at {level}"
                    )


    def test_short_text_chunking(self):
        short_text = """
        Human: Hello! How are you?
        Assistant: I'm doing well, thank you for asking!
        """
        short_chunks = self.compressor._chunk_text(short_text)
        self.assertEqual(len(short_chunks), 1)  # Short text should be one chunk

    def test_medium_text_chunking(self):
        medium_text = """
        Human: Can you explain quantum computing?
        Assistant: Quantum computing is a fascinating field that uses quantum mechanics principles...
        Human: That's interesting! Can you give an example?
        Assistant: A great example is factoring large numbers...
        """
        medium_chunks = self.compressor._chunk_text(medium_text)
        self.assertGreater(len(medium_chunks), 1)  # Medium text should be multiple chunks

    def test_long_text_chunking(self):
        # Create a genuinely long text with many sentences and clear breakpoints
        long_text = "Human: Let's discuss machine learning in great detail.\n"
        long_text += "Assistant: "

        # Create a very long response with multiple distinct sentences
        base_sentences = [
            "Neural networks are fundamental to modern machine learning.",
            "Each layer in a neural network performs specific transformations.",
            "Deep learning has revolutionized artificial intelligence.",
            "Convolutional networks excel at image processing tasks.",
            "Recurrent networks are designed for sequential data.",
            "Transformer models have changed natural language processing.",
            "Attention mechanisms help models focus on relevant information.",
            "Training deep networks requires significant computational resources.",
            "Optimization algorithms help find the best model parameters.",
            "Regularization techniques prevent overfitting in neural networks."
        ]

        # Repeat these sentences many times to create very long text
        long_text += " ".join(base_sentences * 50)  # 500 sentences

        print(f"\nLong text length: {len(long_text)}")  # Debug print
        long_chunks = self.compressor._chunk_text(long_text)
        print(f"Number of chunks: {len(long_chunks)}")  # Debug print

        # Print first few characters of each chunk
        for i, chunk in enumerate(long_chunks):
            print(f"Chunk {i} length: {len(chunk['content'])}")
            print(f"Chunk {i} preview: {chunk['content'][:50]}...")

        self.assertGreater(len(long_chunks), 2)

    def test_compression_ratios(self):
        test_text = """
        Human: Can you explain how compression works?
        Assistant: Let me give you a detailed explanation of compression algorithms and their applications in various scenarios. There are multiple approaches...
        """ * 3

        context = self.compressor.compress(test_text)

        # Check compression metrics
        self.assertIn('compression_ratio', context.metadata)
        self.assertIn('original_tokens', context.metadata)
        self.assertIn('compressed_tokens', context.metadata)
        self.assertTrue(context.metadata['compression_ratio'] > 0)

    def read_full_file(file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def extract_text_content(context: Context) -> str:
        """Extract text content from compressed tokens."""
        text_parts = []
        compression_level = CompressionLevel

        for token in context.compressed_tokens:
            if isinstance(token, dict) and 'content' in token:
                content = token['content']
                speaker = token.get('speaker', '')
                if speaker:
                    text_parts.append(f"{speaker}: {content}")
                else:
                    text_parts.append(content)
            elif isinstance(token, str):
                text_parts.append(token)
        return "\n".join(text_parts)

    def test_compression_settings(self, compression_level: Dict):  # Add self parameter
        total_original = 0
        total_compressed = 0
        similarities = []

        # Define read_full_file helper
        def read_full_file(path: Path) -> str:
            with open(path, 'r') as f:
                return f.read()

        for ctx_file in store_path.glob('*.full'):
            # Read original
            original = read_full_file(ctx_file)

            # Try compression
            compressed_context = self.compressor.compress(original)  # Use self.compressor
            compressed_text = extract_text_content(compressed_context)

            # Measure results
            total_original += len(original)
            total_compressed += len(compressed_text)
            similarities.append(measure_similarity(original, compressed_text))

        return {
            'ratio': total_original / total_compressed,
            'avg_similarity': np.mean(similarities),
            'min_similarity': np.min(similarities)
        }

    def compress_with_settings(text, compression_level):
        compressor = SemanticCompressor()
        compressor.set_compression_level(compression_level)
        return compressor.compress(text).text_content

    def measure_similarity(text1, text2):
        # Implement semantic similarity measurement
        # This is a placeholder implementation
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()


if __name__ == '__main__':
    unittest.main()
