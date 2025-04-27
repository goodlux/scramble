"""
Test script for the FIPA integration features.

This script tests the functionality of the FIPA integration
with MagicScroll and the ActiveConversation class.
"""

import asyncio
import os
import sys
import json
from datetime import datetime, UTC

# Add parent directory to path to import from scramble
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scramble.magicscroll.magic_scroll import MagicScroll
from scramble.magicscroll.ms_fipa import MSFIPAStorage
from scramble.coordinator.active_conversation import ActiveConversation, MessageType
from scramble.coordinator.coordinator import Coordinator


async def test_fipa_storage():
    """Test the FIPA storage functionality."""
    print("\n===== Testing FIPA Storage =====")
    
    # Create a FIPA storage instance
    fipa_storage = MSFIPAStorage()
    
    # Create a conversation
    conversation_id = fipa_storage.create_conversation({
        "test": True,
        "created_at": datetime.now(UTC).isoformat()
    })
    print(f"Created conversation with ID: {conversation_id}")
    
    # Add messages
    message_id1 = fipa_storage.save_message(
        conversation_id,
        "user",
        "test-model",
        "Hello, this is a test message",
        "INFORM",
        {"message_type": "PERMANENT"}
    )
    print(f"Created message with ID: {message_id1}")
    
    message_id2 = fipa_storage.save_message(
        conversation_id,
        "test-model",
        "user",
        "Hello, I'm responding to your test message",
        "INFORM",
        {"message_type": "PERMANENT"}
    )
    print(f"Created message with ID: {message_id2}")
    
    # Get conversation messages
    messages = fipa_storage.get_conversation_messages(conversation_id)
    print(f"Retrieved {len(messages)} messages")
    
    # Print messages (formatted for readability)
    for i, msg in enumerate(messages):
        print(f"\nMessage {i+1}:")
        print(f"  From: {msg['sender']}")
        print(f"  To: {msg['receiver']}")
        print(f"  Content: {msg['content']}")
        print(f"  Timestamp: {msg['timestamp']}")
        print(f"  Metadata: {json.dumps(msg['metadata'], indent=2)}")
    
    # Close conversation
    fipa_storage.close_conversation(conversation_id)
    print(f"Closed conversation: {conversation_id}")
    
    return conversation_id


async def test_active_conversation_with_memory():
    """Test the ActiveConversation class with memory injections."""
    print("\n===== Testing ActiveConversation with Memory =====")
    
    # Create an ActiveConversation instance
    conversation = ActiveConversation()
    print("Created ActiveConversation")
    
    # Add a regular message
    user_msg = await conversation.add_message(
        content="Tell me about quantum computing",
        speaker="user",
        message_type=MessageType.PERMANENT
    )
    print(f"Added user message: {user_msg.message_id}")
    
    # Add a system message
    sys_msg = await conversation.add_system_message(
        content="This is a system message",
        message_type=MessageType.PERMANENT
    )
    print(f"Added system message: {sys_msg.message_id}")
    
    # Add a memory injection
    memory_msg = await conversation.add_memory_injection(
        content="We talked about quantum computing last week. Here's what we said...",
        source_id="test-source-id"
    )
    print(f"Added memory injection: {memory_msg.message_id}")
    
    # Add a coordination message
    coord_msg = await conversation.add_coordination_message(
        content="Please respond to this user's question about quantum computing",
        target_model="test-model"
    )
    print(f"Added coordination message: {coord_msg.message_id}")
    
    # Print all messages
    print("\nAll messages in conversation:")
    for i, msg in enumerate(conversation.messages):
        print(f"\nMessage {i+1}:")
        print(f"  Speaker: {msg.speaker}")
        print(f"  Type: {msg.message_type.value}")
        print(f"  Content: {msg.content[:50]}...")
        print(f"  Message ID: {msg.message_id}")
    
    # Format for storage with filtering
    print("\nFiltered conversation for storage:")
    storage_format = conversation.format_conversation_for_storage()
    print(f"Message count in storage format: {len(storage_format['messages'])}")
    
    # Check which messages were filtered out
    filtered_ids = [msg.message_id for msg in conversation.messages
                   if not any(m.get('message_id') == msg.message_id 
                             for m in storage_format['messages'])]
    print(f"Filtered out message IDs: {filtered_ids}")
    
    return conversation


async def test_magicscroll_fipa_integration():
    """Test the integration between MagicScroll and FIPA."""
    print("\n===== Testing MagicScroll FIPA Integration =====")
    
    try:
        # Create MagicScroll instance
        magic_scroll = await MagicScroll.create()
        print("Created MagicScroll instance")
        
        # Create a FIPA conversation
        conversation_id = magic_scroll.create_fipa_conversation({
            "test": True,
            "created_at": datetime.now(UTC).isoformat()
        })
        print(f"Created FIPA conversation with ID: {conversation_id}")
        
        # Add messages
        magic_scroll.save_fipa_message(
            conversation_id,
            "user",
            "test-model",
            "This is a test message from user",
            "INFORM",
            {"message_type": MessageType.PERMANENT.value}
        )
        
        magic_scroll.save_fipa_message(
            conversation_id,
            "test-model",
            "user",
            "This is a response from the model",
            "INFORM",
            {"message_type": MessageType.PERMANENT.value}
        )
        
        # Add an ephemeral message
        magic_scroll.save_fipa_message(
            conversation_id,
            "system",
            "all",
            "This is an ephemeral context message that should be filtered out",
            "INFORM",
            {"message_type": MessageType.EPHEMERAL.value}
        )
        
        # Get conversation with and without ephemeral messages
        messages_with_ephemeral = magic_scroll.get_fipa_conversation(
            conversation_id, include_ephemeral=True
        )
        messages_without_ephemeral = magic_scroll.get_fipa_conversation(
            conversation_id, include_ephemeral=False
        )
        
        print(f"Retrieved {len(messages_with_ephemeral)} messages with ephemeral")
        print(f"Retrieved {len(messages_without_ephemeral)} messages without ephemeral")
        
        # Save to MagicScroll long-term storage
        entry_id = await magic_scroll.save_fipa_conversation_to_ms(
            conversation_id,
            {"test": True}
        )
        print(f"Saved to MagicScroll with entry ID: {entry_id}")
        
        # Close FIPA conversation
        magic_scroll.close_fipa_conversation(conversation_id)
        print(f"Closed FIPA conversation: {conversation_id}")
        
        # Close MagicScroll
        await magic_scroll.close()
        print("Closed MagicScroll")
        
        return entry_id
    
    except Exception as e:
        print(f"Error in MagicScroll FIPA test: {e}")
        return None


async def test_coordinator():
    """Test the Coordinator with FIPA integration."""
    print("\n===== Testing Coordinator with FIPA =====")
    
    try:
        # Create a Coordinator
        coordinator = await Coordinator.create()
        print("Created Coordinator")
        
        # Check if MagicScroll is available
        if coordinator.magicscroll:
            print("MagicScroll is available")
        else:
            print("MagicScroll is not available - FIPA tests will be limited")
        
        # Start a conversation
        await coordinator.start_conversation()
        print("Started conversation")
        
        # Check if FIPA conversation ID was created
        if coordinator.active_conversation:
            fipa_id = coordinator.active_conversation.fipa_conversation_id
            print(f"FIPA conversation ID: {fipa_id}")
        else:
            print("No active conversation created")
            return None
        
        # Add a test model
        await coordinator.add_model_to_conversation("test-model")
        print("Added test model to conversation")
        
        # Process a test message
        try:
            await coordinator.process_message("This is a test message")
            print("Processed test message")
        except Exception as e:
            print(f"Error processing message: {e}")
        
        # Save conversation to MagicScroll
        entry_id = await coordinator.save_conversation_to_magicscroll()
        print(f"Saved conversation to MagicScroll with entry ID: {entry_id}")
        
        return entry_id
    
    except Exception as e:
        print(f"Error in Coordinator test: {e}")
        return None


async def main():
    """Run all tests."""
    print("===== Running FIPA Integration Tests =====")
    
    # Test FIPA storage
    await test_fipa_storage()
    
    # Test ActiveConversation with memory
    await test_active_conversation_with_memory()
    
    # Test MagicScroll FIPA integration
    await test_magicscroll_fipa_integration()
    
    # Test Coordinator
    # Note: This test may fail if models aren't properly configured
    # await test_coordinator()
    
    print("\n===== All Tests Completed =====")


if __name__ == "__main__":
    asyncio.run(main())
