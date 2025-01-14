#!/usr/bin/env python3
"""
Schema application script for Neo4j
Applies schema files in numerical order from the schema directory
"""

import os
import time
from neo4j import GraphDatabase
from pathlib import Path

def wait_for_neo4j(uri, max_attempts=30, delay=2):
    """Wait for Neo4j to become available"""
    driver = GraphDatabase.driver(uri)
    for attempt in range(max_attempts):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
                print("Neo4j is available!")
                return driver
        except Exception as e:
            print(f"Waiting for Neo4j (attempt {attempt + 1}/{max_attempts})...")
            time.sleep(delay)
    raise Exception("Neo4j failed to become available")

def apply_schema_file(driver, schema_file):
    """Apply a single schema file"""
    print(f"\nApplying schema file: {schema_file.name}")
    
    # Read and split the file into individual statements
    with open(schema_file, 'r') as f:
        content = f.read()
    
    # Simple statement splitting - assumes statements end with semicolon
    # Ignores semicolons in comments
    statements = []
    current_statement = []
    in_multiline_comment = False
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines and single-line comments
        if not line or line.startswith('//'):
            continue
            
        # Handle multi-line comments
        if '/*' in line:
            in_multiline_comment = True
        if '*/' in line:
            in_multiline_comment = False
            continue
        if in_multiline_comment:
            continue
            
        current_statement.append(line)
        
        if line.endswith(';'):
            statement = ' '.join(current_statement)
            statements.append(statement)
            current_statement = []

    # Execute each statement
    with driver.session() as session:
        for statement in statements:
            try:
                print(f"Executing: {statement[:100]}...")  # Print first 100 chars
                session.run(statement)
                print("Success!")
            except Exception as e:
                print(f"Error executing statement: {str(e)}")
                print("Continuing with next statement...")

def main():
    # Configuration
    NEO4J_URI = "neo4j://localhost:7687"
    
    # Get the schema directory path
    script_dir = Path(__file__).resolve().parent
    schema_dir = script_dir.parent / 'schema'
    
    print(f"Looking for schema files in: {schema_dir}")
    
    # Get all .cypher files and sort them
    schema_files = sorted(schema_dir.glob('*.cypher'))
    
    if not schema_files:
        print("No schema files found!")
        return
    
    print(f"Found schema files: {[f.name for f in schema_files]}")
    
    # Wait for Neo4j to be available
    driver = wait_for_neo4j(NEO4J_URI)
    
    # Apply each schema file in order
    for schema_file in schema_files:
        apply_schema_file(driver, schema_file)
    
    driver.close()
    print("\nSchema application complete!")

if __name__ == "__main__":
    main()