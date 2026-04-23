#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import yaml

sys.path.insert(0, ".")

skills_path = Path("C:/Users/DanielaRosenstein/projects/uipath-builder-agent/skills/skills")

for skill_file in skills_path.rglob("SKILL.md"):
    print(f"\nFile: {skill_file}")
    try:
        content = skill_file.read_text()
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            print("  NO FRONTMATTER MATCH")
            continue
        
        parsed = yaml.safe_load(frontmatter_match.group(1))
        if not isinstance(parsed, dict):
            print(f"  NOT A DICT: {type(parsed)}")
            continue
        
        name = parsed.get("name")
        if not name:
            print("  NO NAME")
            continue
        
        print(f"  Name: {name}")
    except Exception as e:
        print(f"  ERROR: {e}")
