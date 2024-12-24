#!/usr/bin/env python3
"""
Enhanced TODO Generator for scRAMble project.
Supports categorization and priority levels.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, NamedTuple
from enum import Enum

class Priority(Enum):
    HIGH = "❗"
    MEDIUM = "⚡"
    LOW = "💭"
    NONE = "📝"

class TodoItem(NamedTuple):
    line: int
    category: str  # Will be "uncategorized" if no category specified
    description: str
    priority: Priority
    done: bool

# Matches both formats:
# TODO(category, priority): description
# TODO: description
TODO_PATTERN = re.compile(
    r'#\s*TODO(?:\((?P<category>[\w-]+)(?:,\s*(?P<priority>high|medium|low))?\))?:\s*(?P<description>.*)'
)

def parse_priority(priority_str: str) -> Priority:
    if not priority_str:
        return Priority.NONE
    return Priority[priority_str.upper()]

def scan_file(filepath: Path) -> List[TodoItem]:
    """Scan a file for TODO comments."""
    todos = []
    with open(filepath, 'r') as f:
        for i, line in enumerate(f, 1):
            if match := TODO_PATTERN.search(line):
                todos.append(TodoItem(
                    line=i,
                    category=match.group('category') or "uncategorized",
                    description=match.group('description').strip(),
                    priority=parse_priority(match.group('priority')),
                    done=False
                ))
    return todos

def generate_markdown(todos_by_file: Dict[str, List[TodoItem]]) -> str:
    """Generate formatted markdown with categorization."""
    sections = [
        "# 🧹 scRAMble Chores List",
        f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "> This file is auto-generated. Edit the TODOs in the source files!\n",
        "## Categories\n"
    ]
    
    # Collect all categories
    categories = set()
    for todos in todos_by_file.values():
        categories.update(todo.category for todo in todos)
    
    # Make sure uncategorized is last if it exists
    categories = sorted(categories - {'uncategorized'}) + (['uncategorized'] if 'uncategorized' in categories else [])
    
    # Generate category summary
    for category in categories:
        sections.append(f"### {category.title()}")
        
        # Group by priority within category
        for priority in Priority:
            category_todos = [
                todo for todos in todos_by_file.values()
                for todo in todos
                if todo.category == category and todo.priority == priority
            ]
            if category_todos:
                sections.append(f"\n{priority.value} Priority {priority.name}:")
                for todo in category_todos:
                    file = next(k for k, v in todos_by_file.items() if todo in v)
                    sections.append(
                        f"- [ ] {todo.description} "
                        f"(`{file}:{todo.line}`)"
                    )
        sections.append("")  # Add spacing between categories
    
    # Add file-based view
    sections.append("## Files")
    for filepath, todos in sorted(todos_by_file.items()):
        clean_path = filepath.replace('\\', '/')
        sections.append(f"\n### {clean_path.split('/')[-1]}")
        sections.append(f"File: `{clean_path}`\n")
        
        for todo in todos:
            category_str = f"({todo.category})" if todo.category != "uncategorized" else ""
            sections.append(
                f"- [ ] {todo.priority.value} {category_str} "
                f"Line {todo.line}: {todo.description}"
            )
    
    return '\n'.join(sections)

def main():
    root_dir = Path(__file__).parent.parent
    todos_by_file = {}
    
    # Scan Python files
    for path in root_dir.rglob('*.py'):
        if 'boneyard' in str(path) or 'venv' in str(path):
            continue
            
        rel_path = path.relative_to(root_dir)
        todos = scan_file(path)
        if todos:
            todos_by_file[str(rel_path)] = todos
    
    # Generate markdown
    markdown = generate_markdown(todos_by_file)
    
    # Write output
    output_path = root_dir / 'docs' / 'DO_THE_CHORES.md'
    output_path.write_text(markdown)
    print(f"Generated TODO list at: {output_path}")

if __name__ == '__main__':
    main()