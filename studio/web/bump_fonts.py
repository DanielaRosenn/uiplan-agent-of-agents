import re
import glob

files = [
    "src/App.tsx",
    "src/components/LeftRail.tsx",
    "src/components/Inspector.tsx",
    "src/components/UiplanCanvas.tsx",
    "src/components/UiplanInspector.tsx",
    "src/components/Canvas.tsx",
    "src/components/ProjectOverview.tsx"
]

def replace_fontsize(m):
    val = float(m.group(1))
    if val < 12:
        return "fontSize: 12"
    return m.group(0)

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # regex to find fontSize: <number>
    new_content = re.sub(r'fontSize:\s*([0-9.]+)', replace_fontsize, content)
    
    if new_content != content:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"Updated {f}")
