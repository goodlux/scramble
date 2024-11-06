import os
import pickle
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, List

def safe_unpickle(file_path: Path) -> Dict[str, Any]:
    """Safely unpickle a context file with error handling."""
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error unpickling {file_path}: {e}")
        return None

def extract_text_content(compressed_tokens: List[Dict[str, Any]]) -> str:
    """Extract text content from compressed tokens."""
    text_parts = []
    for token in compressed_tokens:
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

def create_full_file(context_data: Dict[str, Any], base_path: Path, context_id: str) -> Path:
    """Create a .full file containing the conversation text."""
    full_dir = base_path / 'full'
    full_dir.mkdir(exist_ok=True)

    full_path = full_dir / f"{context_id}.full"

    # Extract metadata
    metadata = {
        'timestamp': context_data.get('created_at', datetime.utcnow()).isoformat(),
        'context_id': context_id,
        'compression_ratio': context_data.get('metadata', {}).get('compression_ratio', 1.0),
        'parent_context': context_data.get('metadata', {}).get('parent_context'),
    }

    # Extract text content
    text_content = extract_text_content(context_data.get('compressed_tokens', []))

    # Write full file with metadata header and content
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write('---\n')
        json.dump(metadata, f, indent=2)
        f.write('\n---\n\n')
        f.write(text_content)

    return full_path

def migrate_contexts(ramble_dir: str = "~/.ramble") -> None:
    """Migrate existing .ctx files to the new storage hierarchy."""
    base_path = Path(ramble_dir).expanduser()
    store_path = base_path / 'store'

    if not store_path.exists():
        print(f"No store directory found at {store_path}")
        return

    # Create new directory structure
    archive_path = store_path / 'archive'
    archive_path.mkdir(exist_ok=True)

    # Process each .ctx file
    for ctx_file in store_path.glob('*.ctx'):
        try:
            # Read original context
            context_data = safe_unpickle(ctx_file)
            if not context_data:
                continue

            context_id = ctx_file.stem

            # Create .full file
            full_path = create_full_file(context_data, store_path, context_id)

            # Move original .ctx to archive
            ctx_file.rename(archive_path / ctx_file.name)

            print(f"Processed {context_id}:")
            print(f"  - Created {full_path}")
            print(f"  - Archived {ctx_file.name}")

        except Exception as e:
            print(f"Error processing {ctx_file}: {e}")

if __name__ == '__main__':
    migrate_contexts()
