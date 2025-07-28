#!/usr/bin/env python3
"""
Fix dependency format in YAML specification files.

Converts string dependencies like 'pydantic@None' to proper DependencyModel format:
{name: 'pydantic', version: None}
"""

import re
import yaml
from pathlib import Path
from typing import Any, Dict, List


def parse_dependency_string(dep_str: str) -> Dict[str, Any]:
    """Parse a dependency string into DependencyModel format.
    
    Examples:
        'pydantic@None' -> {name: 'pydantic', version: None}
        'pytest@latest' -> {name: 'pytest', version: 'latest'}
        'pytest' -> {name: 'pytest'}
    """
    if '@' in dep_str:
        name, version = dep_str.split('@', 1)
        # Convert 'None' string to actual None
        if version == 'None':
            version = None
        return {'name': name, 'version': version}
    else:
        return {'name': dep_str}


def fix_dependencies_in_data(data: Dict[str, Any]) -> bool:
    """Fix dependencies format in YAML data structure.
    
    Returns True if changes were made, False otherwise.
    """
    changes_made = False
    
    if 'context' in data and 'dependencies' in data['context']:
        dependencies = data['context']['dependencies']
        if isinstance(dependencies, list):
            new_dependencies = []
            for dep in dependencies:
                if isinstance(dep, str):
                    # Convert string to proper format
                    new_dep = parse_dependency_string(dep)
                    new_dependencies.append(new_dep)
                    changes_made = True
                    print(f"  Fixed dependency: '{dep}' -> {new_dep}")
                elif isinstance(dep, dict):
                    # Already in correct format
                    new_dependencies.append(dep)
                else:
                    print(f"  Warning: Unexpected dependency format: {dep}")
                    new_dependencies.append(dep)
            
            if changes_made:
                data['context']['dependencies'] = new_dependencies
    
    return changes_made


def fix_yaml_file(file_path: Path) -> bool:
    """Fix a single YAML file.
    
    Returns True if changes were made, False otherwise.
    """
    try:
        print(f"Processing {file_path.name}...")
        
        # Read YAML file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            print(f"  Skipped: Empty or invalid YAML")
            return False
        
        # Fix dependencies
        changes_made = fix_dependencies_in_data(data)
        
        if changes_made:
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            print(f"  ✅ Fixed and saved {file_path.name}")
            return True
        else:
            print(f"  ✓ No changes needed")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {file_path.name}: {e}")
        return False


def main():
    """Fix dependency formats in all YAML specification files."""
    specs_dir = Path("specs")
    if not specs_dir.exists():
        print("❌ specs directory not found")
        return
    
    yaml_files = list(specs_dir.glob("*.yaml"))
    if not yaml_files:
        print("❌ No YAML files found in specs directory")
        return
    
    print(f"Found {len(yaml_files)} YAML files to check...")
    print()
    
    fixed_files = 0
    total_files = 0
    
    for file_path in yaml_files:
        total_files += 1
        if fix_yaml_file(file_path):
            fixed_files += 1
    
    print()
    print(f"📊 Summary:")
    print(f"   Total files: {total_files}")
    print(f"   Fixed files: {fixed_files}")
    print(f"   No changes: {total_files - fixed_files}")
    
    if fixed_files > 0:
        print()
        print("✅ All dependency formats have been fixed!")
        print("   You can now run workflow commands without YAML loading errors.")
    else:
        print()
        print("✅ All dependency formats were already correct!")


if __name__ == "__main__":
    main()