# 🚀 Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
```bash
cd /Users/Rishab_Kshatri/Work2/personal
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
GITHUB_TOKEN=your_github_token_here  # Optional but recommended
EOF
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- GitHub: https://github.com/settings/tokens (need `repo` scope)

### 3. Test Installation
```bash
python -c "from langgraph.graph import StateGraph; print('✅ LangGraph installed')"
python -c "import git; print('✅ GitPython installed')"
```

---

## 🎯 Run Your First Generation

### Option 1: LangChain Release Notes (Recommended for Testing)

```python
from langgraph_implementation import generate_release_notes

# Generate release notes for LangChain v0.1.0 to v0.2.0
result = generate_release_notes(
    repo_url="https://github.com/langchain-ai/langchain",
    from_tag="v0.1.0",
    to_tag="v0.2.0"
)

print(f"✅ Document generated: {result['output_path']}")
```

**Expected Output:**
```
🔄 [INGESTION] Extracting git data...
   Cloning repository to /tmp/doc_generator_repos/langchain...
   Extracting commits between v0.1.0 and v0.2.0...
   Processing 247 commits...
✅ [INGESTION] Extracted 247 commits

🔄 [ENHANCEMENT] Enriching commits with GitHub data...
   Fetching PR data for 247 commits...
   Progress: 0/247
   ...
✅ [ENHANCEMENT] Enriched 247 commits

🔄 [CLASSIFICATION] Categorizing commits with LLM...
   Processing batch 1/9...
✅ [CLASSIFICATION] Categorized 247 commits:
   - feature: 89
   - bug_fix: 52
   - documentation: 31
   - refactoring: 28
   - test: 24
   - chore: 23

🔄 [SUMMARIZER] Generating release notes...
✅ [SUMMARIZER] Generated release notes

🔄 [PUBLISHING] Creating final document...
✅ [PUBLISHING] Document saved to: /tmp/doc_generator_output/release_notes_20250106_143022.md
```

### Option 2: Custom Repository

```python
from langgraph_implementation import generate_release_notes

# Use your own repository
result = generate_release_notes(
    repo_url="https://github.com/your-org/your-repo",
    from_tag="v1.0.0",
    to_tag="v2.0.0"
)
```

---

## 📊 Use Cases

### 1. Release Notes
```python
from langgraph_implementation import build_workflow

app = build_workflow()

state = {
    "repo_url": "https://github.com/langchain-ai/langchain",
    "mode": "release_notes",
    "config": {
        "from_tag": "v0.1.0",
        "to_tag": "v0.2.0"
    },
    "errors": [],
    "warnings": [],
    "raw_commits": [],
    "enriched_commits": [],
    "classified_commits": {},
    "commit_categories": {},
    "summary_sections": {},
    "key_insights": [],
    "repo_metadata": {}
}

result = app.invoke(state, config={"configurable": {"thread_id": "unique_id"}})
print(result["final_document"])
```

### 2. Person-Centric KT
```python
from datetime import datetime

app = build_workflow()

state = {
    "repo_url": "https://github.com/langchain-ai/langchain",
    "mode": "person_centric",
    "config": {
        "author_email": "harrison@langchain.dev",  # Replace with actual email
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 12, 31)
    },
    "errors": [],
    "warnings": [],
    "raw_commits": [],
    "enriched_commits": [],
    "classified_commits": {},
    "commit_categories": {},
    "summary_sections": {},
    "key_insights": [],
    "repo_metadata": {}
}

result = app.invoke(state, config={"configurable": {"thread_id": "person_kt_1"}})
print(result["final_document"])
```

### 3. Feature-Centric KT
```python
app = build_workflow()

state = {
    "repo_url": "https://github.com/langchain-ai/langchain",
    "mode": "feature_centric",
    "config": {
        "file_patterns": ["libs/langchain/langchain/agents/"],
        "feature_name": "Agent Framework"
    },
    "errors": [],
    "warnings": [],
    "raw_commits": [],
    "enriched_commits": [],
    "classified_commits": {},
    "commit_categories": {},
    "summary_sections": {},
    "key_insights": [],
    "repo_metadata": {}
}

result = app.invoke(state, config={"configurable": {"thread_id": "feature_kt_1"}})
print(result["final_document"])
```

---

## 🎓 Test with Different Repositories

### Small Repository (Fast Testing)
```python
# FastAPI - smaller, faster to process
generate_release_notes(
    repo_url="https://github.com/tiangolo/fastapi",
    from_tag="0.100.0",
    to_tag="0.110.0"
)
```

### Medium Repository (Recommended)
```python
# LangChain - good balance
generate_release_notes(
    repo_url="https://github.com/langchain-ai/langchain",
    from_tag="v0.1.0",
    to_tag="v0.2.0"
)
```

### Large Repository (Advanced)
```python
# React - very large, lots of commits
generate_release_notes(
    repo_url="https://github.com/facebook/react",
    from_tag="v18.0.0",
    to_tag="v18.1.0"
)
```

---

## 📈 Compare with Official Release Notes

### LangChain Example

**Official Release Notes:**
https://github.com/langchain-ai/langchain/releases/tag/v0.2.0

**Your Generated Notes:**
`/tmp/doc_generator_output/release_notes_YYYYMMDD_HHMMSS.md`

**Comparison Checklist:**
- [ ] Did it capture all major features?
- [ ] Are bug fixes correctly identified?
- [ ] Are breaking changes highlighted?
- [ ] Is the language clear and professional?
- [ ] Are commit counts accurate?

---

## 🐛 Troubleshooting

### Issue: "Repository not found"
```bash
# Test git access manually
git clone https://github.com/langchain-ai/langchain /tmp/test_clone
# If this fails, check your network/permissions
```

### Issue: "GitHub API rate limit"
```bash
# Check your rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit

# Use authenticated requests (set GITHUB_TOKEN in .env)
```

### Issue: "OpenAI API error"
```bash
# Test your API key
python -c "from openai import OpenAI; print(OpenAI().models.list())"
```

### Issue: "Out of memory"
```python
# Process smaller ranges
generate_release_notes(
    repo_url="...",
    from_tag="v0.2.15",  # Use closer tags
    to_tag="v0.2.16"
)
```

---

## 💰 Cost Estimation

### Per 100 Commits (Approximate)

**With GitHub Enhancement:**
- Classification: ~$0.05 (GPT-4o-mini)
- Summarization: ~$0.15 (GPT-4o)
- **Total: ~$0.20**

**Without GitHub Enhancement:**
- Classification: ~$0.03
- Summarization: ~$0.10
- **Total: ~$0.13**

**LangChain v0.1.0 → v0.2.0 (247 commits):**
- Estimated cost: **~$0.50**

---

## 🚀 Next Steps

### 1. Validate Output Quality
```bash
# Generate for a repo you know well
# Compare with official release notes
# Adjust prompts in langgraph_implementation.py if needed
```

### 2. Customize Prompts
```python
# Edit prompts in langgraph_implementation.py
# Lines to focus on:
# - Line 220: Classification prompt
# - Line 400: Release notes prompt
# - Line 500: Person KT prompt
# - Line 600: Feature KT prompt
```

### 3. Add Custom Categories
```python
# In classification_node, add new categories:
# - security: Security patches, vulnerability fixes
# - performance: Performance improvements
# - deprecation: Deprecated features
```

### 4. Integrate with CI/CD
```yaml
# .github/workflows/release-notes.yml
name: Generate Release Notes
on:
  release:
    types: [published]

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: python generate_release_notes.py ${{ github.event.release.tag_name }}
```

---

## 📚 Additional Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangSmith** (Monitoring): https://smith.langchain.com/
- **Project Strategy**: See `PROJECT_STRATEGY.md` for detailed architecture
- **Implementation**: See `langgraph_implementation.py` for code

---

## 🎯 Success Criteria

Your system is working well if:

✅ Generates documents in < 5 minutes for 100 commits
✅ Categorizes >85% of commits correctly
✅ Captures all major features mentioned in official notes
✅ Produces readable, professional documentation
✅ Handles errors gracefully (repos without tags, API failures)

---

## 💡 Pro Tips

1. **Start Small**: Test with 10-20 commits first
2. **Use LangSmith**: Monitor LLM calls and costs
3. **Cache Results**: Don't re-process same commits
4. **Iterate Prompts**: Spend time refining prompts
5. **Compare Output**: Always compare with human-written docs
6. **Use GPT-4o**: Better quality for summarization
7. **Batch API Calls**: Use batch processing to reduce latency

---

## 🤝 Getting Help

If you run into issues:

1. Check error messages in terminal
2. Look at `state["errors"]` and `state["warnings"]`
3. Test each node individually
4. Use LangSmith to debug LLM calls
5. Check GitHub API rate limits
6. Verify API keys are correct

---

**Ready to generate your first automated documentation!** 🎉

Run:
```bash
python langgraph_implementation.py
```

