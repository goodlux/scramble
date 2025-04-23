import ast
import os
import json
from pathlib import Path

# Walk through the repo and get all files
def list_files(root_dir, additional_paths=[]):
    """ Recursively list all Python files in the repo and additional paths (excluding virtual envs and non-Python files). """
    excluded_dirs = ['venv', '__pycache__']
    python_files = [str(f) for f in Path(root_dir).rglob("*") 
                    if f.is_file() and f.suffix == ".py" and not any(ex in str(f) for ex in excluded_dirs)]
    
    # Add extra paths (like llama_index) only if we want full repo plus externals
    for path in additional_paths:
        if Path(path).exists():
            python_files.extend([str(f) for f in Path(path).rglob("*") if f.is_file() and f.suffix == ".py"])

    return python_files

# Extract symbols (functions, classes) and relevant docstrings, including function parameters
def extract_symbols_and_docs(file_path):
    """ Parse the file using AST and extract classes, functions, their docstrings, and parameters. """
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)
    
    symbols = {
        "functions": [],
        "classes": [],
        "docstrings": [],
        "todos": [],
        "imports": []
    }

    for node in ast.walk(tree):
        # Extract functions, parameters and their docstrings
        if isinstance(node, ast.FunctionDef):
            params = []
            for i, arg in enumerate(node.args.args):
                # Safely extract parameter default values (if any)
                default_value = None
                if i >= len(node.args.defaults):
                    default_value = None
                else:
                    default_value = ast.dump(node.args.defaults[i])  # Get the default value of the parameter
                params.append({
                    "name": arg.arg,
                    "default": default_value
                })
            symbols["functions"].append({
                "name": node.name,
                "parameters": params,
                "docstring": ast.get_docstring(node)
            })
        # Extract classes and their docstrings
        elif isinstance(node, ast.ClassDef):
            symbols["classes"].append({
                "name": node.name,
                "docstring": ast.get_docstring(node)
            })
        # Collect TODO and FIXME comments
        elif isinstance(node, ast.Constant) and node.value and isinstance(node.value, str) and (node.value.lower().startswith("todo") or "fixme" in node.value.lower()):
            symbols["todos"].append(node.value)
        # Collect imports
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            for alias in node.names:
                symbols["imports"].append(alias.name)
    
    return symbols

# Generate a structured index of the codebase for the given paths
def generate_code_index(root_dir, extra_paths=[]):
    """ Main function to generate the codebase index. """
    repo_index = {}

    # Generate index for root repo only
    python_files = list_files(root_dir, [])
    
    # Loop over each file and extract symbols for the root project
    for file_path in python_files:
        symbols = extract_symbols_and_docs(file_path)
        repo_index[file_path] = symbols
    
    return repo_index

# Generate a structured index only for additional paths (excluding the main repo)
def generate_external_index(extra_paths):
    """ Generate index only for the given external paths (no root project files). """
    external_index = {}

    # Loop over each additional path (like llama_index)
    for path in extra_paths:
        python_files = list_files("", [path])  # Only look at files in the extra path, no root project files
        
        for file_path in python_files:
            symbols = extract_symbols_and_docs(file_path)
            external_index[file_path] = symbols
    
    return external_index

# Save the index to a JSON file with a directory-specific name
def save_to_json(data, output_dir, filename):
    """ Save the generated index to a JSON file in the specified directory. """
    output_path = Path(output_dir) / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Main entry point
if __name__ == "__main__":
    # Path to your local repo and extra paths for external dependencies
    repo_path = "."
    extra_paths = [
        '/Users/rob/repos/scramble/.venv/lib/python3.12/site-packages/llama_index'
    ]
    
    # Generate code index for root repo (scramble)
    print(f"Generating code index for {repo_path} and additional paths...")

    # Generate index for root repo (scramble)
    root_index = generate_code_index(repo_path, [])
    save_to_json(root_index, "docs/index", "scramble_index.json")
    
    # Generate index for each external path (like llama_index)
    for extra_path in extra_paths:
        external_index = generate_external_index([extra_path])
        # The file name will reflect the external path's name (e.g., llama_index becomes llama_index_ext_index.json)
        external_filename = f"{Path(extra_path).name}_ext_index.json"
        save_to_json(external_index, "docs/index", external_filename)

    print("Code indexes saved in docs/index/ directory.")
