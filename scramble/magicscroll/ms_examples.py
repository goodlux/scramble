# import asyncio
# from .magic_scroll import MagicScroll
# from typing import List, Dict, Any, Optional, Union

# async def test_magicscroll():
#     # Initialize MagicScroll
#     scroll = MagicScroll()
    
#     # Write some test conversations
#     conv1_id = await scroll.write_conversation(
#         "The consciousness and quantum physics conversation about test 123."
#     )
#     print(f"Added first conversation: {conv1_id}")

#     conv2_id = await scroll.write_conversation(
#         "Neural networks and artificial brains test ABC."
#     )
#     print(f"Added second conversation: {conv2_id}")
    
#     # Test semantic search
#     print("\nSemantic Search Results':")
#     print("\nSearching for 'consciousness':")
#     results = await scroll.remember("consciousness and the mind", limit=2, min_score=0.0)  # Set min_score to 0
#     print(f"Found {len(results)} results")
#     for idx, result in enumerate(results, 1):
#         print(f"\nResult {idx}:")
#         print(f"Score: {result['score']:.3f}")
#         #print(f"Content: {result['entry'].content}")
#         print(f"Created: {result['entry'].created_at}")

#     # Add a second different search to test
#     print("\nSemantic Search Results':")
#     print("\nSearching for 'neural networks':")
#     results = await scroll.remember("neural networks", limit=2, min_score=0.0)  # Set min_score to 0
#     print(f"Found {len(results)} results")
#     for idx, result in enumerate(results, 1):
#         print(f"\nResult {idx}:")
#         print(f"Score: {result['score']:.3f}")
#         #print(f"Content: {result['entry'].content}")
#         print(f"Created: {result['entry'].created_at}")

# # Run the test
# if __name__ == "__main__":
#     asyncio.run(test_magicscroll())