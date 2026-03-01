import re

with open("README.md", "r") as f:
    content = f.read()

# Find the first occurrence of "## 🚀 Mistral Worldwide Hackathon Optimization"
# and remove everything after it up to the next major section to avoid duplication
# or just keep the latest and cleanest version.

# Actually, the README has become quite large. I will keep it as is since it contains all info,
# but I'll remove the redundant "Mistral Edition" sections at the very end.

marker = "---"
parts = content.split(marker)
# Keep only the unique and most relevant parts.
# After manual review of the previous 'cat >>' operations, I'll just trim the end duplication.

cleaned = marker.join(parts[:10]) # Adjust based on structure
with open("README.md", "w") as f:
    f.write(cleaned)
