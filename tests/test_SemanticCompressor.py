import unittest
import numpy as np
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from scramble.core import stats
from scramble.core.context import Context  # Add this
from scramble.core.compressor import SemanticCompressor
from scramble.core.compressor import CompressionLevel
from tests.utils.results_manager import ResultsManager

# Define store path
store_path = Path.home() / '.ramble' / 'store'

class TestSemanticCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = SemanticCompressor()
        self.store_path = Path.home() / '.ramble' / 'store'
        self.results = ResultsManager()


    def test_compression_settings_with_levels(self):
        """Test compression with different settings across all stored contexts."""
        test_conversations = [
            # Short conversation
            """
            Human: Hi there!
            Assistant: Hello! How can I help you today?
            """,

            # Medium conversation with multiple turns
            """
            Human: Can you explain quantum computing?
            Assistant: Quantum computing uses quantum mechanics principles like superposition and entanglement.
            Human: What's superposition?
            Assistant: Superposition means a quantum bit can be in multiple states at once.
            """,

            # Long technical conversation
            """
            Human: Let's discuss machine learning in detail.
            Assistant: I'll explain several key concepts in machine learning.
            First, let's talk about supervised learning...
            [Long technical explanation]
            There are also neural networks, which...
            [Another detailed section]
            And finally, we have reinforcement learning...
            """,

            # Conversation with repeated patterns
            """
            Human: What's the weather today?
            Assistant: Today will be sunny with a high of 75°F.
            Human: How about tomorrow?
            Assistant: Tomorrow will also be sunny with a high of 73°F.
            Human: And the next day?
            Assistant: The next day will continue to be sunny with a high of 72°F.
            """
        ]

        level_results = {}

        for level in ['LOW', 'MEDIUM', 'HIGH']:
            self.compressor.set_compression_level(level)

            level_results = {
                'ratios': [],
                'similarities': [],
                'chunk_counts': []
            }

            for text in test_conversations:
                # Skip empty texts
                if not text.strip():
                    continue

                # Compress and analyze
                context = self.compressor.compress(text)

                # Gather metrics
                level_results['ratios'].append(context.metadata['compression_ratio'])
                level_results['similarities'].append(context.metadata['semantic_similarity'])
                level_results['chunk_counts'].append(len(context.compressed_tokens))

            # Store average results
            avg_results = {
                'avg_ratio': np.mean(level_results['ratios']),
                'avg_similarity': np.mean(level_results['similarities']),
                'avg_chunks': np.mean(level_results['chunk_counts'])
            }
            self.results.store_level_result(level, avg_results)



            # Validate level-specific expectations
            current_results = self.results.get_level_result(level)

            if level == 'LOW':
                self.assertGreater(
                    current_results['avg_similarity'], 0.8,
                    "Low compression should maintain high similarity"
                )
                self.assertLess(
                    current_results['avg_ratio'], 2.0,
                    "Low compression should not be too aggressive"
                )

            elif level == 'MEDIUM':
                self.assertGreater(
                    current_results['avg_similarity'], 0.7,
                    "Medium compression should maintain good similarity"
                )
                self.assertGreater(
                    current_results['avg_ratio'], 1.5,
                    "Medium compression should achieve reasonable reduction"
                )

            elif level == 'HIGH':
                self.assertGreater(
                    current_results['avg_similarity'], 0.6,
                    "High compression should maintain acceptable similarity"
                )
                self.assertGreater(
                    current_results['avg_ratio'], 2.0,
                    "High compression should achieve significant reduction"
                )

            # Compare relationships between levels
            if level != 'LOW':

                prev_level = 'MEDIUM' if level == 'HIGH' else 'LOW'
                prev_results = self.results.get_level_result(prev_level)

                self.assertGreater(
                    current_results['avg_ratio'],
                    prev_results['avg_ratio'],
                    f"{level} compression should be more aggressive than {prev_level}"
                )
                self.assertLessEqual(
                    current_results['avg_similarity'],
                    prev_results['avg_similarity'],
                    f"{level} compression should have lower or equal similarity to {prev_level}"
                )

            passed=True  # You might want to calculate this based on assertions


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

    def test_compression_settings(self):
        """Test different compression levels and their effectiveness."""
        test_text = """
        Human: Hello! How are you?
        Assistant: I'm doing well, thank you for asking!
        Human: Can you explain quantum computing?
        Assistant: Quantum computing is a fascinating field that uses quantum mechanics...
        """

        # Test each compression level
        for level in ['LOW', 'MEDIUM', 'HIGH']:
            with self.subTest(level=level):
                # Set compression level
                self.compressor.set_compression_level(level)

                # Compress text
                context = self.compressor.compress(test_text)

                # Calculate metrics
                original_length = len(test_text)
                compressed_length = sum(len(chunk['content'])
                                     for chunk in context.compressed_tokens)
                compression_ratio = context.metadata['compression_ratio']
                similarity = context.metadata['semantic_similarity']

                # Basic validation
                self.assertGreater(compressed_length, 0,
                    f"{level}: Got empty compression")
                self.assertGreater(compression_ratio, 0,
                    f"{level}: Invalid compression ratio")
                self.assertGreater(similarity, 0.5,
                    f"{level}: Poor semantic preservation")

                # Level-specific validation
                if level == 'LOW':
                    self.assertGreater(compression_ratio, 1.0,
                        "Low compression should preserve most content")
                elif level == 'HIGH':
                    self.assertGreater(compression_ratio, 2.0,
                        "High compression should be more aggressive")

                self.results.save_compression_result(
                                f"compression_settings_{level}",
                                metrics={
                                    'level': level,
                                    'original_length': original_length,
                                    'compressed_length': compressed_length,
                                    'compression_ratio': compression_ratio,
                                    'similarity': similarity
                                },
                                expectations={
                                    'compression_ratio': 2.0 if level == 'HIGH' else 1.0,
                                    'min_similarity': 0.5
                                },
                                passed=all([
                                    compressed_length > 0,
                                    compression_ratio > 0,
                                    similarity > 0.5
                                ])
                            )


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
                with self.subTest(case=name, level=level):  # This is key!
                    self.compressor.set_compression_level(level)
                    context = self.compressor.compress(text)

                    stats = {
                        'test_case': name,
                        'compression_level': level,
                        'original_length': len(text),
                        'compressed_length': context.metadata['compressed_length'],
                        'compression_ratio': context.metadata['compression_ratio'],
                        'semantic_similarity': context.metadata['semantic_similarity'],
                        'timestamp': datetime.now().isoformat()
                    }

                    metrics = {
                        'test_case': name,
                        'compression_level': level,
                        'original_length': len(text),
                        'compressed_length': context.metadata['compressed_length'],
                        'compression_ratio': context.metadata['compression_ratio'],
                        'semantic_similarity': context.metadata['semantic_similarity'],
                        'num_chunks': len(context.compressed_tokens),
                        'original_tokens': context.metadata['original_tokens'],
                        'compressed_tokens': context.metadata['compressed_tokens'],
                        'token_reduction': context.metadata['original_tokens'] / context.metadata['compressed_tokens'],
                        'detailed_chunks': [
                            {
                                'size': len(chunk['content']),
                                'speaker': chunk.get('speaker', 'unknown'),
                                'preview': chunk['content'][:50] + '...' if len(chunk['content']) > 50 else chunk['content']
                            } for chunk in context.compressed_tokens
                        ]
                    }

                    expectations = {
                        'min_semantic_similarity': self.compressor.semantic_threshold,
                        'min_compression_ratio': 2.0 if level == 'HIGH' else None,
                        'expected_thresholds': {
                            'HIGH': {'similarity': 0.6, 'ratio': 2.0, 'max_chunk_size': 16},
                            'MEDIUM': {'similarity': 0.7, 'ratio': 1.5, 'max_chunk_size': 64},
                            'LOW': {'similarity': 0.8, 'ratio': None, 'max_chunk_size': 265}
                        },
                        'level_specific': {
                            'compression_targets': {
                                'HIGH': 2.0,
                                'MEDIUM': 1.5,
                                'LOW': 1.0
                            },
                            'similarity_targets': {
                                'HIGH': 0.6,
                                'MEDIUM': 0.7,
                                'LOW': 0.8
                            }
                        }
                    }

                    # Determine if test passed
                    passed = all([
                        context.metadata['semantic_similarity'] > self.compressor.semantic_threshold,
                        context.metadata['semantic_similarity'] >= expectations['expected_thresholds'][level]['similarity'],
                        level != 'HIGH' or context.metadata['compression_ratio'] > 2.0,
                        all(len(chunk['content']) <= expectations['expected_thresholds'][level]['max_chunk_size']
                            for chunk in context.compressed_tokens)
                    ])

                    # Save results
                    self.results.save_compression_result(
                        f"{name}_{level}",
                        metrics,
                        expectations,
                        passed
                    )

                    # Print summary
                    print(f"\nTesting {name} at {level}:")
                    print(f"Original length: {len(text)}")
                    print(f"Compressed length: {context.metadata['compressed_length']}")
                    print(f"Compression ratio: {context.metadata['compression_ratio']:.2f}x")
                    print(f"Semantic similarity: {context.metadata['semantic_similarity']:.2f}")
                    print(f"Test passed: {passed}")

                    # Assertions
                    self.assertGreater(
                        context.metadata['semantic_similarity'],
                        self.compressor.semantic_threshold,
                        f"Lost too much meaning in {name} at {level}"
                    )

                    if level == 'HIGH':
                        self.assertGreater(
                            context.metadata['compression_ratio'],
                            2.0,
                            f"Not enough compression for {name} at {level}"
                        )

    def test_short_text_chunking(self):
        """Test chunking of very short conversations."""
        short_text = """
        Human: Hello! How are you?
        Assistant: I'm doing well, thank you for asking!
        """
        chunks = self.compressor._chunk_text(short_text)
        self.assertEqual(len(chunks), 1,
            "Short text should produce single chunk")
        self.assertEqual(chunks[0]['speaker'], 'Assistant',
            "Final speaker should be preserved")

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

    def read_full_file(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def extract_text_content(self, context: Context) -> str:
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


    def compress_with_settings(self, text, compression_level):
        compressor = SemanticCompressor()
        compressor.set_compression_level(compression_level)
        return compressor.compress(text).text_content

    def measure_similarity(self, text1, text2):
        # Implement semantic similarity measurement
        # This is a placeholder implementation
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()



if __name__ == '__main__':
    unittest.main()
