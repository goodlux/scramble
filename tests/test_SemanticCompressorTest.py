import unittest
import numpy as np
from datetime import datetime, timedelta

from scramble.core.compressor import SemanticCompressor

class TestSemanticCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = SemanticCompressor()

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
