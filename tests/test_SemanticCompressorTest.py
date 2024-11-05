import unittest
import numpy as np
from datetime import datetime, timedelta

from scramble.core.compressor import SemanticCompressor

class TestSemanticCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = SemanticCompressor()

    def test_adaptive_chunking(self):
        # Short conversation
        short_text = """
        Human: Hello! How are you?
        Assistant: I'm doing well, thank you for asking!
        """

        # Medium conversation
        medium_text = """
        Human: Can you explain quantum computing?
        Assistant: Quantum computing is a fascinating field that uses quantum mechanics principles. Unlike classical computers that use bits (0 or 1), quantum computers use qubits which can exist in multiple states simultaneously through superposition. This allows them to perform certain calculations much faster than classical computers.
        Human: That's interesting! Can you give an example?
        Assistant: A great example is factoring large numbers. Classical computers struggle with this, but quantum computers using Shor's algorithm can do it much more efficiently. This has important implications for cryptography and security.
        """

        # Long conversation
        long_text = """
        Human: Let's have an in-depth discussion about machine learning architectures.
        """ + "Assistant: " + " ".join(["detailed explanation"] * 1000)

        # Test chunk sizes
        short_chunks = self.compressor._chunk_text(short_text)
        medium_chunks = self.compressor._chunk_text(medium_text)
        long_chunks = self.compressor._chunk_text(long_text)

        self.assertLess(len(short_chunks), len(medium_chunks))
        self.assertLess(len(medium_chunks), len(long_chunks))

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

    def test_similarity_scoring(self):
        # Create two related and one unrelated conversation
        conv1 = """
        Human: Let's talk about Python programming.
        Assistant: Python is a versatile programming language known for its readability.
        """

        conv2 = """
        Human: What are some good Python libraries for data science?
        Assistant: Popular Python libraries include NumPy, Pandas, and Scikit-learn.
        """

        conv3 = """
        Human: What's your favorite recipe for chocolate cake?
        Assistant: Here's a delicious chocolate cake recipe with detailed instructions...
        """

        # Compress all conversations
        context1 = self.compressor.compress(conv1)
        context2 = self.compressor.compress(conv2)
        context3 = self.compressor.compress(conv3)

        # Test similarity with a Python-related query
        query = "Can you help me with Python programming?"
        similar = self.compressor.find_similar(
            query,
            [context1, context2, context3]
        )

        # Python-related conversations should score higher
        python_scores = [score for _, score, _ in similar[:2]]
        cake_score = [score for _, score, _ in similar if score == similar[-1][1]][0]

        for python_score in python_scores:
            self.assertGreater(python_score, cake_score)

    def test_time_based_scoring(self):
        # Create contexts with different timestamps
        text = "Human: Test conversation\nAssistant: Test response"

        now = datetime.utcnow()
        recent_context = self.compressor.compress(text, {
            'timestamp': now.isoformat()
        })

        old_context = self.compressor.compress(text, {
            'timestamp': (now - timedelta(days=5)).isoformat()
        })

        # Find similar with time weighting
        similar = self.compressor.find_similar(
            "Test",
            [recent_context, old_context],
            recency_weight=0.5
        )

        # Recent context should score higher
        self.assertEqual(similar[0][0].id, recent_context.id)

if __name__ == '__main__':
    unittest.main()
