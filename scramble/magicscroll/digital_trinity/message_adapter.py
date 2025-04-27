"""
Message adapter for converting between different messaging formats and FIPA ACL.

This module provides conversion utilities between FIPA ACL messages and various
AI model messaging formats (OpenAI, Anthropic, etc.) to enable seamless integration
between different models and the core messaging system.
"""

import json
from typing import Dict, Any, List, Optional, Union, Tuple

from .fipa_acl import FIPAACLMessage

class MessageAdapter:
    """Adapter for converting between message formats"""
    
    @staticmethod
    def openai_to_fipa(
        openai_msg: Dict[str, Any],
        conversation_id: Optional[str] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None
    ) -> FIPAACLMessage:
        """
        Convert OpenAI format message to FIPA ACL.
        
        Args:
            openai_msg: Message in OpenAI format
            conversation_id: Optional conversation ID
            sender: Optional sender ID (derived from role if not provided)
            receiver: Optional receiver ID
            
        Returns:
            FIPA ACL message
        """
        # Map role to sender/receiver if not explicitly provided
        if not sender:
            sender = f"agent:{openai_msg['role']}"
        
        # Map OpenAI role to FIPA performative
        role_to_performative = {
            'system': 'INFORM',
            'user': 'REQUEST',
            'assistant': 'INFORM',
            'function': 'INFORM_REF',
            'tool': 'INFORM_REF'  # For newer OpenAI API versions
        }
        
        performative = role_to_performative.get(openai_msg['role'], 'INFORM')
        
        # Handle function calls specially
        if 'function_call' in openai_msg:
            performative = 'REQUEST'
            content = json.dumps({
                'text': openai_msg.get('content', ''),
                'function_call': openai_msg['function_call']
            })
        elif 'tool_calls' in openai_msg:  # For newer OpenAI API versions
            performative = 'REQUEST'
            content = json.dumps({
                'text': openai_msg.get('content', ''),
                'tool_calls': openai_msg['tool_calls']
            })
        else:
            content = openai_msg.get('content', '')
        
        # Create message with appropriate metadata
        msg = FIPAACLMessage(
            performative=performative,
            sender=sender,
            receiver=receiver,
            content=content,
            conversation_id=conversation_id
        )
        
        # Add original format as metadata
        msg.metadata = {
            'original_format': 'openai',
            'original_role': openai_msg['role']
        }
        
        return msg
    
    @staticmethod
    def fipa_to_openai(fipa_msg: FIPAACLMessage) -> Dict[str, Any]:
        """
        Convert FIPA ACL message to OpenAI format.
        
        Args:
            fipa_msg: FIPA ACL message
            
        Returns:
            Message in OpenAI format
        """
        # Check if there's metadata about the original format
        if fipa_msg.metadata.get('original_format') == 'openai':
            role = fipa_msg.metadata.get('original_role', 'user')
        else:
            # Map FIPA performative to OpenAI role
            performative_to_role = {
                'INFORM': 'assistant',
                'REQUEST': 'user',
                'QUERY_REF': 'user',
                'INFORM_REF': 'function',
                'CONFIRM': 'assistant',
                'DISCONFIRM': 'assistant',
                'AGREE': 'assistant',
                'REFUSE': 'assistant',
                'FAILURE': 'assistant',
                'NOT_UNDERSTOOD': 'assistant'
            }
            
            role = performative_to_role.get(fipa_msg.performative, 'user')
        
        # Check if this is a function call or tool call
        try:
            content_json = json.loads(fipa_msg.content)
            if isinstance(content_json, dict):
                if 'function_call' in content_json:
                    return {
                        'role': role,
                        'content': content_json.get('text', ''),
                        'function_call': content_json['function_call']
                    }
                elif 'tool_calls' in content_json:
                    return {
                        'role': role,
                        'content': content_json.get('text', ''),
                        'tool_calls': content_json['tool_calls']
                    }
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Standard message
        return {
            'role': role,
            'content': fipa_msg.content
        }
    
    @staticmethod
    def anthropic_to_fipa(
        anthropic_msg: Dict[str, Any],
        conversation_id: Optional[str] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None
    ) -> FIPAACLMessage:
        """
        Convert Anthropic format message to FIPA ACL.
        
        Args:
            anthropic_msg: Message in Anthropic format
            conversation_id: Optional conversation ID
            sender: Optional sender ID (derived from role if not provided)
            receiver: Optional receiver ID
            
        Returns:
            FIPA ACL message
        """
        # Map role to sender/receiver if not explicitly provided
        if not sender:
            role = anthropic_msg.get('role', 'user')
            sender = f"agent:{role}"
        
        # Map Anthropic role to FIPA performative
        role_to_performative = {
            'assistant': 'INFORM',
            'user': 'REQUEST',
            'system': 'INFORM',
        }
        
        role = anthropic_msg.get('role', 'user')
        performative = role_to_performative.get(role, 'INFORM')
        
        # Handle content which could be string or complex structure
        if isinstance(anthropic_msg.get('content', []), list):
            # Process the content blocks
            text_parts = []
            tool_calls = []
            
            for block in anthropic_msg.get('content', []):
                if block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
                elif block.get('type') == 'tool_use':
                    tool_calls.append(block)
            
            if tool_calls:
                performative = 'REQUEST'
                content = json.dumps({
                    'text': '\n'.join(text_parts),
                    'tool_calls': tool_calls
                })
            else:
                content = '\n'.join(text_parts)
        else:
            # Simple string content
            content = anthropic_msg.get('content', '')
        
        # Create message with appropriate metadata
        msg = FIPAACLMessage(
            performative=performative,
            sender=sender,
            receiver=receiver,
            content=content,
            conversation_id=conversation_id
        )
        
        # Add original format as metadata
        msg.metadata = {
            'original_format': 'anthropic',
            'original_role': role
        }
        
        return msg
    
    @staticmethod
    def fipa_to_anthropic(fipa_msg: FIPAACLMessage) -> Dict[str, Any]:
        """
        Convert FIPA ACL message to Anthropic format.
        
        Args:
            fipa_msg: FIPA ACL message
            
        Returns:
            Message in Anthropic format
        """
        # Check if there's metadata about the original format
        if fipa_msg.metadata.get('original_format') == 'anthropic':
            role = fipa_msg.metadata.get('original_role', 'user')
        else:
            # Map FIPA performative to Anthropic role
            performative_to_role = {
                'INFORM': 'assistant',
                'REQUEST': 'user',
                'QUERY_REF': 'user',
                'CONFIRM': 'assistant',
                'DISCONFIRM': 'assistant',
                'AGREE': 'assistant',
                'REFUSE': 'assistant',
                'FAILURE': 'assistant',
                'NOT_UNDERSTOOD': 'assistant'
            }
            
            role = performative_to_role.get(fipa_msg.performative, 'user')
        
        # Check if this is a tool call
        try:
            content_json = json.loads(fipa_msg.content)
            if isinstance(content_json, dict) and 'tool_calls' in content_json:
                text = content_json.get('text', '')
                tool_calls = content_json['tool_calls']
                
                # Format as Anthropic content blocks
                content = []
                
                # Add text block if present
                if text:
                    content.append({
                        'type': 'text',
                        'text': text
                    })
                
                # Add tool_use blocks
                for tool_call in tool_calls:
                    content.append({
                        'type': 'tool_use',
                        'id': tool_call.get('id', ''),
                        'name': tool_call.get('function', {}).get('name', ''),
                        'input': tool_call.get('function', {}).get('arguments', '{}')
                    })
                
                return {
                    'role': role,
                    'content': content
                }
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Standard message
        return {
            'role': role,
            'content': [{'type': 'text', 'text': fipa_msg.content}]
        }
    
    @staticmethod
    def mcp_to_fipa(
        mcp_msg: Dict[str, Any],
        conversation_id: Optional[str] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None
    ) -> FIPAACLMessage:
        """
        Convert MCP protocol message to FIPA ACL.
        
        Args:
            mcp_msg: Message in MCP format
            conversation_id: Optional conversation ID
            sender: Optional sender ID
            receiver: Optional receiver ID
            
        Returns:
            FIPA ACL message
        """
        # Default sender/receiver if not provided
        if not sender:
            sender = "agent:mcp_client"
        if not receiver:
            receiver = "agent:mcp_server"
        
        # Determine performative based on MCP message type
        if 'request' in mcp_msg:
            performative = 'REQUEST'
            content_data = mcp_msg['request']
        elif 'response' in mcp_msg:
            performative = 'INFORM'
            content_data = mcp_msg['response']
        elif 'error' in mcp_msg:
            performative = 'FAILURE'
            content_data = mcp_msg['error']
        else:
            performative = 'INFORM'
            content_data = mcp_msg
        
        # Serialize content to JSON string
        content = json.dumps(content_data)
        
        # Create message with appropriate metadata
        msg = FIPAACLMessage(
            performative=performative,
            sender=sender,
            receiver=receiver,
            content=content,
            conversation_id=conversation_id
        )
        
        # Add original format as metadata
        msg.metadata = {
            'original_format': 'mcp',
            'mcp_version': mcp_msg.get('version', '1.0')
        }
        
        return msg
    
    @staticmethod
    def fipa_to_mcp(fipa_msg: FIPAACLMessage) -> Dict[str, Any]:
        """
        Convert FIPA ACL message to MCP format.
        
        Args:
            fipa_msg: FIPA ACL message
            
        Returns:
            Message in MCP format
        """
        # Parse content
        try:
            content = json.loads(fipa_msg.content)
        except (json.JSONDecodeError, TypeError):
            content = {'text': fipa_msg.content}
        
        # Map performative to MCP message type
        if fipa_msg.performative == 'REQUEST':
            return {
                'version': fipa_msg.metadata.get('mcp_version', '1.0'),
                'request': content
            }
        elif fipa_msg.performative == 'FAILURE':
            return {
                'version': fipa_msg.metadata.get('mcp_version', '1.0'),
                'error': content
            }
        else:  # INFORM and others
            return {
                'version': fipa_msg.metadata.get('mcp_version', '1.0'),
                'response': content
            }
    
    @staticmethod
    def a2a_to_fipa(
        a2a_msg: Dict[str, Any],
        conversation_id: Optional[str] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None
    ) -> FIPAACLMessage:
        """
        Convert Google's A2A protocol message to FIPA ACL.
        
        Args:
            a2a_msg: Message in A2A format
            conversation_id: Optional conversation ID
            sender: Optional sender ID
            receiver: Optional receiver ID
            
        Returns:
            FIPA ACL message
        """
        # This is a placeholder implementation that would need to be
        # updated once A2A specifications are more widely available
        
        # Default sender/receiver if not provided
        if not sender:
            sender = "agent:a2a_client"
        if not receiver:
            receiver = "agent:a2a_server"
        
        # Determine performative based on A2A message type
        if 'task' in a2a_msg:
            performative = 'REQUEST'
            content_data = a2a_msg['task']
        elif 'result' in a2a_msg:
            performative = 'INFORM'
            content_data = a2a_msg['result']
        elif 'error' in a2a_msg:
            performative = 'FAILURE'
            content_data = a2a_msg['error']
        else:
            performative = 'INFORM'
            content_data = a2a_msg
        
        # Serialize content to JSON string
        content = json.dumps(content_data)
        
        # Create message with appropriate metadata
        msg = FIPAACLMessage(
            performative=performative,
            sender=sender,
            receiver=receiver,
            content=content,
            conversation_id=conversation_id
        )
        
        # Add original format as metadata
        msg.metadata = {
            'original_format': 'a2a',
            'a2a_version': a2a_msg.get('version', '1.0')
        }
        
        return msg
    
    @staticmethod
    def fipa_to_a2a(fipa_msg: FIPAACLMessage) -> Dict[str, Any]:
        """
        Convert FIPA ACL message to A2A format.
        
        Args:
            fipa_msg: FIPA ACL message
            
        Returns:
            Message in A2A format
        """
        # This is a placeholder implementation that would need to be
        # updated once A2A specifications are more widely available
        
        # Parse content
        try:
            content = json.loads(fipa_msg.content)
        except (json.JSONDecodeError, TypeError):
            content = {'text': fipa_msg.content}
        
        # Map performative to A2A message type
        if fipa_msg.performative == 'REQUEST':
            return {
                'version': fipa_msg.metadata.get('a2a_version', '1.0'),
                'task': content
            }
        elif fipa_msg.performative == 'FAILURE':
            return {
                'version': fipa_msg.metadata.get('a2a_version', '1.0'),
                'error': content
            }
        else:  # INFORM and others
            return {
                'version': fipa_msg.metadata.get('a2a_version', '1.0'),
                'result': content
            }
