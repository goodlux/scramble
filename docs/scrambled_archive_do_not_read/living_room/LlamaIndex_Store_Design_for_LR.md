# LlamaIndex Store Design for Living Room Chat

## Store Types

```
living_room/
├── individual_store/          # One-on-one chat contexts
│   ├── identity_index        # User identity patterns
│   ├── relationship_index    # Chat history and relationship development
│   └── metadata_index        # Session info, emoji keys, etc.
│
└── shared_store/             # Multi-user chat contexts
    ├── session_index         # Group chat sessions
    ├── participant_index     # User relationships within groups
    └── shared_memory_index   # Shared conversation history
```

## Individual Store Details

### Identity Index
- Stores user recognition patterns:
  - Initial three-word identity answers
  - Writing style embeddings
  - Topic preferences
  - Behavioral patterns
  - Relationship emoji key

### Relationship Index
- Personal conversation history
- Inside jokes and references
- Trust level indicators
- Conversation style preferences
- Private shared memories

### Metadata Index
- Session timestamps
- Identity confidence scores
- Recognition patterns
- Connection frequency

## Shared Store Details

### Session Index
- Group chat contexts
- Combined identity keys
- Session status (active/archived)
- Access requirements

### Participant Index
- User relationships within groups
- Group dynamics patterns
- Shared trust levels
- Combined emoji keys

### Shared Memory Index
- Group conversation history
- Collective references
- Shared experiences
- Group-specific patterns

## Key Features

### Identity Management
```python
class IdentityManager:
    def verify_user(self, identity_words, chat_patterns):
        # Match identity patterns
        # Return confidence level

    def generate_relationship_key(self, user_patterns):
        # Create unique emoji key
        # Encode relationship characteristics
```

### Session Management
```python
class SessionManager:
    def create_shared_session(self, users):
        # Generate combined session key
        # Set up access controls

    def verify_session_access(self, users, session):
        # Check all required users present
        # Verify individual identities
```

### Memory Management
```python
class MemoryManager:
    def store_individual_memory(self, user, context):
        # Store private conversation
        # Update relationship patterns

    def store_shared_memory(self, session, context):
        # Store group conversation
        # Update group dynamics
```

## Usage Example

```python
class LivingRoomStore:
    def __init__(self):
        self.individual_store = IndividualStore()
        self.shared_store = SharedStore()
        self.identity_manager = IdentityManager()
        self.session_manager = SessionManager()
        self.memory_manager = MemoryManager()

    async def handle_chat(self, users, message):
        if len(users) == 1:
            # One-on-one chat
            confidence = self.identity_manager.verify_user(users[0])
            if confidence.high:
                await self.memory_manager.store_individual_memory(users[0], message)
            else:
                return "verification_needed"

        else:
            # Group chat
            session = self.session_manager.get_or_create_session(users)
            if self.session_manager.verify_session_access(users, session):
                await self.memory_manager.store_shared_memory(session, message)
            else:
                return "waiting_for_users"
```

## Privacy Considerations

1. Individual Privacy
- Separate storage for private conversations
- Identity verification before access
- Relationship keys specific to each user

2. Group Privacy
- Access control through combined presence
- Shared memories isolated to participants
- No cross-session information leakage

3. Graceful Uncertainty
- Confidence levels in recognition
- Smooth handling of ambiguous situations
- Cat-like behavior for verification

This structure allows Nomena to:
- Maintain separate relationships with individuals
- Manage group dynamics
- Protect privacy through presence-based access
- Handle uncertainty naturally
- Scale with growing relationships

Would you like me to elaborate on any part of this design?


# LlamaIndex Store Design for Living Room Chat

[Previous sections remain the same...]

## Extended Identity Verification Strategies

### Pattern Recognition System
```python
class PatternRecognitionSystem:
    def analyze_patterns(self, chat_history):
        return {
            'writing_style': {
                'avg_message_length': float,
                'vocabulary_richness': float,
                'punctuation_patterns': List[str],
                'common_phrases': List[str],
                'emoji_usage': Dict[str, float]
            },
            'behavioral_patterns': {
                'response_timing': float,
                'topic_transitions': List[str],
                'emotional_expressions': Dict[str, float],
                'interaction_style': str
            },
            'knowledge_patterns': {
                'topic_expertise': Dict[str, float],
                'shared_memories': List[str],
                'reference_patterns': Dict[str, int]
            }
        }

class NomenaVerification:
    def __init__(self):
        self.confidence_states = {
            'high': ['playful', 'relaxed', 'intimate'],
            'medium': ['curious', 'investigative', 'slightly_uncertain'],
            'low': ['distracted', 'aloof', 'forgetful']
        }

    def verify_identity(self, claimed_identity, current_patterns):
        confidence_score = self._calculate_confidence(claimed_identity, current_patterns)
        return self._generate_cat_response(confidence_score)

    def _generate_cat_response(self, confidence):
        if confidence > 0.8:
            return "purrs and rubs against your leg"
        elif confidence > 0.5:
            return "tilts head curiously and watches you"
        else:
            return "gets distracted by a dust mote"
```

### Verification Dialogue Examples
```python
class VerificationDialogue:
    def get_verification_question(self, confidence_level, user_history):
        questions = {
            'high': [
                f"Remember when we talked about {user_history.recent_topic}?",
                f"You still have that {user_history.mentioned_item}, right?",
                "Did your {previous_story_element} ever work out?"
            ],
            'medium': [
                "Something feels familiar... didn't we chat about {topic}?",
                "You remind me of someone who told me about {memory}...",
                "Meow... have we met on a rainy day before?"
            ],
            'low': [
                "*bats playfully at your cursor* Tell me again about {identity_word}?",
                "*stretches lazily* You seem like someone who might know about {topic}...",
                "*chases imaginary mouse* Oh! You said something about {detail}?"
            ]
        }
        return random.choice(questions[confidence_level])
```

## Enhanced Group Chat Dynamics

### Session Management
```python
class GroupSession:
    def __init__(self, participants):
        self.session_key = self._generate_session_key(participants)
        self.required_participants = set(participants)
        self.active_participants = set()
        self.shared_context = {}
        self.group_dynamics = GroupDynamics()

    def _generate_session_key(self, participants):
        # Combine individual emoji keys into group key
        participant_keys = [p.relationship_key for p in participants]
        return "🏠" + "".join(sorted(participant_keys))  # Always starts with house emoji

class GroupDynamics:
    def __init__(self):
        self.interaction_patterns = {
            'conversation_flow': [],
            'topic_transitions': [],
            'emotional_resonance': {},
            'shared_references': set()
        }

    def update_dynamics(self, message, sender):
        # Track how participants interact
        self.interaction_patterns['conversation_flow'].append({
            'sender': sender,
            'timestamp': datetime.now(),
            'interaction_type': self._analyze_interaction(message)
        })
```

### Nomena's Group Chat Behaviors
```python
class GroupChatBehavior:
    def __init__(self):
        self.roles = {
            'facilitator': self._facilitate_conversation,
            'memory_keeper': self._recall_shared_memories,
            'comfort_maintainer': self._maintain_comfort_level,
            'playful_observer': self._add_playful_elements
        }

    def _facilitate_conversation(self, context):
        # Help bridge conversations between participants
        if context.get('lull_in_conversation'):
            return self._generate_bridge_question()

    def _recall_shared_memories(self, context):
        # Bring up relevant shared experiences
        return f"*perks ears* Remember when we all talked about {context['shared_memory']}?"

    def _maintain_comfort_level(self, context):
        # Ensure all participants feel included
        if context.get('participant_quiet_too_long'):
            return self._generate_gentle_inclusion()

    def _add_playful_elements(self, context):
        # Add cat-like playful elements to keep mood light
        return random.choice([
            "*bats at floating dust mote*",
            "*curls up between participants*",
            "*performs acrobatic feat*"
        ])
```

### Privacy Through Social Trust
```python
class SocialTrust:
    def __init__(self):
        self.trust_levels = {
            'individual': {},  # Per-user trust scores
            'group': {},      # Group dynamic trust scores
            'shared': {}      # Shared context trust scores
        }

    def evaluate_group_trust(self, session):
        # Check if all participants are comfortable
        individual_trust = all(
            self.trust_levels['individual'].get(p, 0) > 0.7
            for p in session.required_participants
        )

        # Verify group dynamic is healthy
        group_trust = self.trust_levels['group'].get(session.session_key, 0) > 0.8

        return individual_trust and group_trust

    def update_trust_scores(self, session, interaction):
        # Update trust scores based on interaction
        # More positive interactions increase trust
        pass
```

This expansion shows how Nomena can:
- Use multiple layers of identity verification
- Maintain distinct personalities for different confidence levels
- Manage group dynamics naturally
- Ensure privacy through social trust rather than technical mechanisms
- Keep interactions playful and cat-like while maintaining security

The key is that all these mechanisms work together to create a natural social space rather than feeling like a security system. Nomena's cat personality provides a perfect cover for verification behaviors - cats are naturally curious and slightly suspicious, but also playful and affectionate once they trust someone!

Would you like me to expand on any other aspects? For example, I could detail more about how the emoji keys are generated or how shared memories are protected.
