# 🚀 Quick Reference Cheatsheet

## ⚡ Get Started in 3 Commands

```bash
pip install -r requirements.txt
cp env_template.txt .env  # Edit and add your API keys
python langgraph_implementation.py
```

---

## 📋 Common Commands

### Generate Release Notes
```python
from langgraph_implementation import generate_release_notes

# LangChain (recommended for testing)
generate_release_notes(
    "https://github.com/langchain-ai/langchain",
    "v0.1.0", "v0.2.0"
)

# FastAPI (faster, smaller)
generate_release_notes(
    "https://github.com/tiangolo/fastapi",
    "0.100.0", "0.110.0"
)

# Your repo
generate_release_notes(
    "https://github.com/your-org/your-repo",
    "v1.0.0", "v2.0.0"
)
```

### Generate Person-Centric KT
```python
from langgraph_implementation import build_workflow
from datetime import datetime

app = build_workflow()

result = app.invoke({
    "repo_url": "https://github.com/langchain-ai/langchain",
    "mode": "person_centric",
    "config": {
        "author_email": "harrison@langchain.dev",
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 12, 31)
    },
    "errors": [], "warnings": [],
    "raw_commits": [], "enriched_commits": [],
    "classified_commits": {}, "commit_categories": {},
    "summary_sections": {}, "key_insights": [],
    "repo_metadata": {}
})
```

### Generate Feature-Centric KT
```python
result = app.invoke({
    "repo_url": "https://github.com/langchain-ai/langchain",
    "mode": "feature_centric",
    "config": {
        "file_patterns": ["libs/langchain/langchain/agents/"],
        "feature_name": "Agent Framework"
    },
    "errors": [], "warnings": [],
    "raw_commits": [], "enriched_commits": [],
    "classified_commits": {}, "commit_categories": {},
    "summary_sections": {}, "key_insights": [],
    "repo_metadata": {}
})
```

---

## 🔧 Configuration

### API Keys (in .env)
```bash
OPENAI_API_KEY=sk-...        # Required
GITHUB_TOKEN=ghp_...         # Optional but recommended
```

### Models
```python
# Fast & cheap (classification)
ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Better quality (summarization)
ChatOpenAI(model="gpt-4o", temperature=0.3)

# Alternative: Claude
from langchain_anthropic import ChatAnthropic
ChatAnthropic(model="claude-3-5-sonnet-20241022")
```

---

## 📊 Output Locations

```
/tmp/doc_generator_output/
├── release_notes_20250106_143022.md
├── person_centric_20250106_150130.md
└── feature_centric_20250106_152045.md
```

---

## 🐛 Quick Troubleshooting

### Problem: "No module named 'langgraph'"
```bash
pip install -r requirements.txt
```

### Problem: "OpenAI API error"
```bash
# Check your .env file
cat .env

# Verify key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10] + '...')"
```

### Problem: "Repository not found"
```bash
# Test git access
git ls-remote https://github.com/langchain-ai/langchain
```

### Problem: "GitHub rate limit"
```bash
# Add GITHUB_TOKEN to .env
# Check limit: curl https://api.github.com/rate_limit
```

### Problem: "Too slow"
```python
# Process fewer commits
generate_release_notes(
    repo_url="...",
    from_tag="v0.2.15",  # Closer tags
    to_tag="v0.2.16"
)

# Or skip GitHub enhancement
# Comment out line 170 in langgraph_implementation.py
```

---

## 💰 Cost Estimates

| Commits | Time | Cost (GPT-4o-mini + GPT-4o) |
|---------|------|----------------------------|
| 10      | 30s  | $0.05                      |
| 50      | 2m   | $0.15                      |
| 100     | 4m   | $0.30                      |
| 250     | 8m   | $0.60                      |
| 500     | 15m  | $1.20                      |

---

## 📈 Performance Tips

### 1. Use Caching
```bash
# Repos cached in /tmp/doc_generator_repos/
# Delete to force fresh clone
rm -rf /tmp/doc_generator_repos/
```

### 2. Skip GitHub Enhancement
```python
# Set GITHUB_TOKEN="" in .env
# Saves ~30% time but loses PR context
```

### 3. Batch Processing
```python
# Already implemented in classification_node
# Processes 30 commits per LLM call
```

### 4. Use Cheaper Model
```python
# In classification_node (line 220)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
# Saves ~70% cost, slightly lower quality
```

---

## 🎯 Test Repositories

### Small (Fast Testing)
```python
"https://github.com/tiangolo/fastapi"
# Tags: 0.100.0, 0.110.0, 0.115.0
# ~50 commits between versions
```

### Medium (Recommended)
```python
"https://github.com/langchain-ai/langchain"
# Tags: v0.1.0, v0.2.0, v0.3.0
# ~200 commits between versions
# Has official release notes for comparison
```

### Large (Advanced)
```python
"https://github.com/facebook/react"
# Tags: v18.0.0, v18.1.0, v18.2.0
# ~500+ commits between major versions
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| README.md | Project overview & features |
| QUICKSTART.md | Setup & first run |
| PROJECT_STRATEGY.md | Architecture & decisions |
| SUMMARY.md | What you have & next steps |
| CHEATSHEET.md | This file - quick reference |
| langgraph_implementation.py | Full working code |

---

## 🔍 Find Things

### Find all tags in a repo
```python
from git import Repo
repo = Repo("/tmp/doc_generator_repos/langchain")
tags = [tag.name for tag in repo.tags]
print(sorted(tags)[-10:])  # Last 10 tags
```

### Find top contributors
```python
from collections import Counter
commits = list(repo.iter_commits('--all', max_count=100))
authors = [c.author.email for c in commits]
print(Counter(authors).most_common(5))
```

### Find directories (for feature-centric)
```python
from pathlib import Path
head = repo.head.commit
files = [item.path for item in head.tree.traverse() if item.type == 'blob']
dirs = set(Path(f).parts[0] for f in files if len(Path(f).parts) > 1)
print(sorted(dirs))
```

---

## ✅ Success Checklist

Before running:
- [ ] Installed requirements.txt
- [ ] Created .env with OPENAI_API_KEY
- [ ] (Optional) Added GITHUB_TOKEN to .env
- [ ] Verified API keys work

After first run:
- [ ] Found output in /tmp/doc_generator_output/
- [ ] Output contains release notes
- [ ] No errors in terminal
- [ ] Compared with official release notes (if available)

---

## 🚀 Quick Commands Reference

```bash
# Setup
pip install -r requirements.txt
cp env_template.txt .env  # Edit this!

# Run
python langgraph_implementation.py

# View output
ls /tmp/doc_generator_output/
cat /tmp/doc_generator_output/release_notes_*.md

# Clean cache
rm -rf /tmp/doc_generator_repos/

# Test API keys
python -c "from openai import OpenAI; print('OK')"

# Check git tags
cd /tmp/doc_generator_repos/langchain && git tag --list
```

---

## 💡 Pro Tips

1. **Start with LangChain** - Has existing release notes to compare
2. **Use small tag ranges** - Test with 10-50 commits first
3. **Check official notes** - Compare your output with human-written
4. **Monitor costs** - Use LangSmith to track API usage
5. **Iterate prompts** - Adjust prompts in langgraph_implementation.py
6. **Cache repos** - Second run is much faster
7. **Use GitHub token** - Better quality with PR descriptions

---

## 🎯 Common Use Cases

### Weekly Release Notes
```python
# Run every Friday
generate_release_notes(
    repo_url="your-repo",
    from_tag="v1.2.0",
    to_tag="v1.3.0"
)
```

### Developer Handover
```python
# When someone leaves
app.invoke({
    "mode": "person_centric",
    "config": {
        "author_email": "leaving-dev@company.com",
        "start_date": datetime(2023, 1, 1),  # Their whole tenure
        "end_date": datetime.now()
    }
})
```

### New Developer Onboarding
```python
# Document a feature they'll work on
app.invoke({
    "mode": "feature_centric",
    "config": {
        "file_patterns": ["src/payments/"],
        "feature_name": "Payment Processing"
    }
})
```

---

**Keep this file open while working!** 📌

