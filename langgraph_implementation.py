"""
LangGraph Implementation for Automated Documentation Generator
Ready-to-use pipeline for generating release notes and KT documents
"""

import os
from typing import TypedDict, List, Dict, Literal, Annotated
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import json

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Git and GitHub imports
import git
from git import Repo
from github import Github


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """Shared state across all agents in the workflow"""
    
    # Input configuration
    repo_url: str
    mode: Literal["release_notes", "person_centric", "feature_centric"]
    config: Dict
    
    # Ingestion stage outputs
    raw_commits: List[Dict]
    repo_metadata: Dict
    
    # Enhancement stage outputs
    enriched_commits: List[Dict]
    
    # Classification stage outputs
    classified_commits: Dict[str, List[Dict]]
    commit_categories: Dict[str, str]
    
    # Summarization stage outputs
    summary_sections: Dict[str, str]
    key_insights: List[str]
    
    # Publishing stage outputs
    final_document: str
    output_path: str
    
    # Error tracking
    errors: List[str]
    warnings: List[str]


# ============================================================================
# NODE 1: INGESTION
# ============================================================================

def ingestion_node(state: AgentState) -> AgentState:
    """
    Extract git commits and repository metadata.
    Handles cloning, commit extraction based on mode.
    """
    print("🔄 [INGESTION] Extracting git data...")
    
    try:
        # Clone or use existing repo
        repo_path = Path("/tmp/doc_generator_repos") / state["repo_url"].split("/")[-1].replace(".git", "")
        
        if not repo_path.exists():
            print(f"   Cloning repository to {repo_path}...")
            Repo.clone_from(state["repo_url"], repo_path)
        else:
            print(f"   Using existing repository at {repo_path}")
        
        repo = Repo(repo_path)
        
        # Extract commits based on mode
        raw_commits = []
        
        if state["mode"] == "release_notes":
            # Extract commits between tags
            from_tag = state["config"]["from_tag"]
            to_tag = state["config"]["to_tag"]
            
            print(f"   Extracting commits between {from_tag} and {to_tag}...")
            
            from_commit = repo.tags[from_tag].commit
            to_commit = repo.tags[to_tag].commit
            
            commit_range = f"{from_commit.hexsha}..{to_commit.hexsha}"
            commits = list(repo.iter_commits(commit_range, no_merges=True))
            
        elif state["mode"] == "person_centric":
            # Extract commits by author
            author_email = state["config"]["author_email"]
            start_date = state["config"].get("start_date")
            end_date = state["config"].get("end_date")
            
            print(f"   Extracting commits by {author_email}...")
            
            kwargs = {"author": author_email, "all": True, "no_merges": True}
            if start_date:
                kwargs["since"] = start_date
            if end_date:
                kwargs["until"] = end_date
            
            commits = list(repo.iter_commits(**kwargs))
            
        else:  # feature_centric
            # Extract commits for specific paths/keywords
            file_patterns = state["config"]["file_patterns"]
            
            print(f"   Extracting commits for patterns: {file_patterns}...")
            
            all_commits = set()
            for pattern in file_patterns:
                commits = list(repo.iter_commits("--all", paths=pattern, no_merges=True))
                all_commits.update(commits)
            
            commits = list(all_commits)
        
        # Parse commits into structured format
        print(f"   Processing {len(commits)} commits...")
        
        for commit in commits:
            # Parse message
            message_lines = commit.message.strip().split('\n', 1)
            subject = message_lines[0]
            body = message_lines[1].strip() if len(message_lines) > 1 else ""
            
            # Get file changes
            if commit.parents:
                diffs = commit.diff(commit.parents[0])
            else:
                diffs = commit.diff(git.NULL_TREE)
            
            files_changed = []
            for diff in diffs:
                change_type = 'M'
                if diff.new_file:
                    change_type = 'A'
                elif diff.deleted_file:
                    change_type = 'D'
                elif diff.renamed_file:
                    change_type = 'R'
                
                files_changed.append({
                    "path": diff.b_path or diff.a_path,
                    "change_type": change_type,
                    "old_path": diff.a_path if change_type == 'R' else None
                })
            
            raw_commits.append({
                "sha": commit.hexsha,
                "author": {
                    "name": commit.author.name,
                    "email": commit.author.email,
                },
                "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "message_subject": subject,
                "message_body": body,
                "files_changed": files_changed,
            })
        
        # Get repo metadata
        state["repo_metadata"] = {
            "name": repo_path.name,
            "path": str(repo_path),
            "branches": [b.name for b in repo.branches],
            "total_commits_processed": len(raw_commits)
        }
        
        state["raw_commits"] = raw_commits
        
        print(f"✅ [INGESTION] Extracted {len(raw_commits)} commits")
        
    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        print(f"❌ [INGESTION] {error_msg}")
        state["errors"].append(error_msg)
    
    return state


# ============================================================================
# NODE 2: ENHANCEMENT (Optional but valuable)
# ============================================================================

def enhancement_node(state: AgentState) -> AgentState:
    """
    Enrich commits with GitHub PR/issue metadata.
    Optional node - can be skipped if GitHub token not available.
    """
    print("🔄 [ENHANCEMENT] Enriching commits with GitHub data...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("⚠️  [ENHANCEMENT] No GitHub token found, skipping enhancement")
        state["enriched_commits"] = state["raw_commits"]
        state["warnings"].append("GitHub enhancement skipped - no token")
        return state
    
    try:
        gh = Github(github_token)
        
        # Extract repo name from URL
        repo_name = "/".join(state["repo_url"].split("/")[-2:]).replace(".git", "")
        repo = gh.get_repo(repo_name)
        
        enriched = []
        
        print(f"   Fetching PR data for {len(state['raw_commits'])} commits...")
        
        for i, commit in enumerate(state["raw_commits"]):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(state['raw_commits'])}")
            
            try:
                # Get commit from GitHub
                gh_commit = repo.get_commit(commit["sha"])
                
                # Find associated PRs
                prs = list(gh_commit.get_pulls())
                
                pr_data = None
                if prs:
                    pr = prs[0]
                    pr_data = {
                        "number": pr.number,
                        "title": pr.title,
                        "description": pr.body or "",
                        "labels": [label.name for label in pr.labels],
                        "url": pr.html_url
                    }
                
                enriched.append({
                    **commit,
                    "pr_data": pr_data
                })
                
            except Exception as e:
                # If GitHub API fails, use original commit
                state["warnings"].append(f"Failed to enrich {commit['sha'][:7]}: {str(e)}")
                enriched.append(commit)
        
        state["enriched_commits"] = enriched
        print(f"✅ [ENHANCEMENT] Enriched {len(enriched)} commits")
        
    except Exception as e:
        error_msg = f"Enhancement failed: {str(e)}"
        print(f"⚠️  [ENHANCEMENT] {error_msg}")
        state["enriched_commits"] = state["raw_commits"]
        state["warnings"].append(error_msg)
    
    return state


# ============================================================================
# NODE 3: CLASSIFICATION
# ============================================================================

def classification_node(state: AgentState) -> AgentState:
    """
    Classify commits into categories using LLM.
    Categories: feature, bug_fix, documentation, refactoring, test, chore, breaking_change
    """
    print("🔄 [CLASSIFICATION] Categorizing commits with LLM...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Prepare commits for classification
        commits = state.get("enriched_commits", state["raw_commits"])
        
        # Batch processing for efficiency
        batch_size = 30
        all_classifications = {}
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a git commit classifier. Categorize each commit into exactly ONE category:
            
            Categories:
            - feature: New functionality, capabilities, or enhancements
            - bug_fix: Bug fixes, error corrections, patches
            - documentation: Documentation changes, README updates, comments
            - refactoring: Code restructuring, cleanup, optimization (no behavior change)
            - test: Test additions, test fixes, test improvements
            - chore: Maintenance, dependencies, build config, tooling
            - breaking_change: Changes that break backward compatibility
            
            Return ONLY a JSON object mapping commit SHA to category.
            Format: {{"sha1": "category1", "sha2": "category2"}}"""),
            ("user", """Classify these commits:\n\n{commits}""")
        ])
        
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i+batch_size]
            
            print(f"   Processing batch {i//batch_size + 1}/{(len(commits)-1)//batch_size + 1}...")
            
            # Format commits for LLM
            commit_text = "\n\n".join([
                f"SHA: {c['sha'][:7]}\n"
                f"Message: {c['message_subject']}\n"
                f"Body: {c['message_body'][:100]}\n"
                f"Files changed: {len(c['files_changed'])} - {', '.join([f['path'] for f in c['files_changed'][:3]])}"
                + (f"\nPR Title: {c.get('pr_data', {}).get('title', '')}" if c.get('pr_data') else "")
                for c in batch
            ])
            
            chain = prompt | llm | JsonOutputParser()
            
            try:
                response = chain.invoke({"commits": commit_text})
                
                # Handle response format variations
                if isinstance(response, dict):
                    all_classifications.update(response)
                elif isinstance(response, list):
                    for item in response:
                        if isinstance(item, dict) and 'sha' in item and 'category' in item:
                            all_classifications[item['sha']] = item['category']
                
            except Exception as e:
                print(f"   ⚠️  Batch classification failed: {e}")
                # Fallback: simple rule-based classification
                for c in batch:
                    all_classifications[c['sha'][:7]] = classify_commit_simple(c)
        
        # Group commits by category
        categorized = defaultdict(list)
        
        for commit in commits:
            sha_short = commit['sha'][:7]
            category = all_classifications.get(sha_short, all_classifications.get(commit['sha'], 'chore'))
            
            categorized[category].append(commit)
            
            # Also check for breaking changes in message
            if any(marker in commit['message_subject'].lower() for marker in ['breaking', 'breaking:', '!:']):
                if commit not in categorized['breaking_change']:
                    categorized['breaking_change'].append(commit)
        
        state["classified_commits"] = dict(categorized)
        state["commit_categories"] = all_classifications
        
        # Print summary
        print(f"✅ [CLASSIFICATION] Categorized {len(commits)} commits:")
        for category, commits_list in categorized.items():
            print(f"   - {category}: {len(commits_list)}")
        
    except Exception as e:
        error_msg = f"Classification failed: {str(e)}"
        print(f"❌ [CLASSIFICATION] {error_msg}")
        state["errors"].append(error_msg)
        
        # Fallback: simple classification
        state["classified_commits"] = {"all": state.get("enriched_commits", state["raw_commits"])}
    
    return state


def classify_commit_simple(commit: Dict) -> str:
    """Simple rule-based classification fallback"""
    msg = commit['message_subject'].lower()
    
    if any(word in msg for word in ['feat', 'feature', 'add', 'implement']):
        return 'feature'
    elif any(word in msg for word in ['fix', 'bug', 'patch', 'resolve']):
        return 'bug_fix'
    elif any(word in msg for word in ['docs', 'documentation', 'readme']):
        return 'documentation'
    elif any(word in msg for word in ['refactor', 'cleanup', 'reorganize']):
        return 'refactoring'
    elif any(word in msg for word in ['test', 'testing']):
        return 'test'
    else:
        return 'chore'


# ============================================================================
# NODE 4: ROUTER
# ============================================================================

def router_node(state: AgentState) -> str:
    """Route to appropriate summarization node based on mode"""
    mode = state["mode"]
    
    if mode == "release_notes":
        return "release_summarizer"
    elif mode == "person_centric":
        return "person_summarizer"
    elif mode == "feature_centric":
        return "feature_summarizer"
    else:
        return "release_summarizer"  # Default


# ============================================================================
# NODE 5a: RELEASE NOTES SUMMARIZER
# ============================================================================

def release_summarizer_node(state: AgentState) -> AgentState:
    """Generate release notes from classified commits"""
    print("🔄 [SUMMARIZER] Generating release notes...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
        classified = state["classified_commits"]
        
        def format_commits(commits: List[Dict], max_items: int = 30) -> str:
            """Format commits for LLM context"""
            if not commits:
                return "None"
            
            return "\n".join([
                f"- {c['message_subject']}"
                + (f" (PR #{c['pr_data']['number']})" if c.get('pr_data') else "")
                + f" by {c['author']['name']}"
                for c in commits[:max_items]
            ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a technical writer creating professional release notes.
            
            Guidelines:
            - Write clear, concise bullet points
            - Focus on USER IMPACT, not implementation details
            - Group related changes together
            - Highlight breaking changes prominently
            - Use active voice
            - Keep descriptions under 15 words
            
            Format each bullet as: "- <Action> <Feature/Component> <Optional: context>"
            Example: "- Added OAuth2 authentication for enterprise users"
            """),
            ("user", """Create release notes for version {version}.
            
            ## New Features
            {features}
            
            ## Bug Fixes
            {bug_fixes}
            
            ## Documentation
            {documentation}
            
            ## Breaking Changes
            {breaking_changes}
            
            Generate professional release notes with sections for each category.
            Include a brief summary at the top (2-3 sentences).
            """)
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "version": state["config"].get("to_tag", "Next Release"),
            "features": format_commits(classified.get("feature", [])),
            "bug_fixes": format_commits(classified.get("bug_fix", [])),
            "documentation": format_commits(classified.get("documentation", [])),
            "breaking_changes": format_commits(classified.get("breaking_change", []))
        })
        
        state["summary_sections"] = {
            "release_notes": response.content
        }
        
        # Generate key insights
        state["key_insights"] = [
            f"📦 {len(classified.get('feature', []))} new features",
            f"🐛 {len(classified.get('bug_fix', []))} bug fixes",
            f"⚠️  {len(classified.get('breaking_change', []))} breaking changes",
            f"📚 {len(classified.get('documentation', []))} documentation updates",
            f"👥 {len(set(c['author']['email'] for c in state['enriched_commits']))} contributors"
        ]
        
        print(f"✅ [SUMMARIZER] Generated release notes")
        
    except Exception as e:
        error_msg = f"Summarization failed: {str(e)}"
        print(f"❌ [SUMMARIZER] {error_msg}")
        state["errors"].append(error_msg)
        state["summary_sections"] = {"release_notes": "Error generating release notes"}
    
    return state


# ============================================================================
# NODE 5b: PERSON-CENTRIC SUMMARIZER
# ============================================================================

def person_summarizer_node(state: AgentState) -> AgentState:
    """Generate person-centric KT document"""
    print("🔄 [SUMMARIZER] Generating person-centric KT...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
        commits = state.get("enriched_commits", state["raw_commits"])
        author_email = state["config"]["author_email"]
        
        # Analyze contributions
        module_stats = defaultdict(lambda: {"commits": 0, "files": set()})
        for commit in commits:
            for file in commit["files_changed"]:
                module = Path(file["path"]).parts[0] if file["path"] else "root"
                module_stats[module]["commits"] += 1
                module_stats[module]["files"].add(file["path"])
        
        # Format for LLM
        modules_text = "\n".join([
            f"- {module}/: {stats['commits']} commits across {len(stats['files'])} files"
            for module, stats in sorted(module_stats.items(), key=lambda x: x[1]["commits"], reverse=True)[:10]
        ])
        
        recent_work = "\n".join([
            f"- {c['timestamp'][:10]}: {c['message_subject']}"
            for c in commits[:20]
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are creating a Knowledge Transfer document for a developer leaving or transitioning.
            
            Structure:
            1. Developer Overview (expertise, focus areas)
            2. Key Contributions (major features/projects)
            3. Code Ownership (files/modules they own)
            4. Ongoing Work (recent commits, in-progress items)
            5. Handover Recommendations (who should take over what)
            
            Be specific, actionable, and highlight business impact."""),
            ("user", """Create KT document for: {author_email}
            
            Period: {period}
            Total Commits: {total_commits}
            
            Modules worked on:
            {modules}
            
            Recent work:
            {recent_work}
            """)
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "author_email": author_email,
            "period": f"{commits[0]['timestamp'][:10]} to {commits[-1]['timestamp'][:10]}",
            "total_commits": len(commits),
            "modules": modules_text,
            "recent_work": recent_work
        })
        
        state["summary_sections"] = {"kt_document": response.content}
        state["key_insights"] = [
            f"👤 {commits[0]['author']['name']}",
            f"📊 {len(commits)} commits",
            f"📁 {len(module_stats)} modules",
            f"📅 Active from {commits[0]['timestamp'][:10]} to {commits[-1]['timestamp'][:10]}"
        ]
        
        print(f"✅ [SUMMARIZER] Generated person-centric KT")
        
    except Exception as e:
        error_msg = f"Person summarization failed: {str(e)}"
        print(f"❌ [SUMMARIZER] {error_msg}")
        state["errors"].append(error_msg)
    
    return state


# ============================================================================
# NODE 5c: FEATURE-CENTRIC SUMMARIZER
# ============================================================================

def feature_summarizer_node(state: AgentState) -> AgentState:
    """Generate feature-centric documentation"""
    print("🔄 [SUMMARIZER] Generating feature documentation...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
        commits = state.get("enriched_commits", state["raw_commits"])
        
        # Analyze contributors
        contributor_stats = defaultdict(lambda: {"commits": 0})
        for commit in commits:
            contributor_stats[commit["author"]["email"]]["commits"] += 1
        
        contributors_text = "\n".join([
            f"- {author}: {stats['commits']} commits"
            for author, stats in sorted(contributor_stats.items(), key=lambda x: x[1]["commits"], reverse=True)[:10]
        ])
        
        timeline_text = "\n".join([
            f"- {c['timestamp'][:10]}: {c['message_subject']}"
            for c in commits[:20]
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are documenting a software feature/module.
            
            Structure:
            1. Feature Overview (what it does, why it exists)
            2. Architecture (components, dependencies)
            3. Evolution Timeline (major milestones)
            4. Contributors (key people and their roles)
            5. Current State (status, known issues, future work)
            
            Be technical but clear. Focus on helping new developers understand the feature."""),
            ("user", """Document the feature: {feature_name}
            
            Total Commits: {total_commits}
            Time Range: {time_range}
            
            Contributors:
            {contributors}
            
            Timeline:
            {timeline}
            """)
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "feature_name": state["config"].get("feature_name", "Feature"),
            "total_commits": len(commits),
            "time_range": f"{commits[0]['timestamp'][:10]} to {commits[-1]['timestamp'][:10]}",
            "contributors": contributors_text,
            "timeline": timeline_text
        })
        
        state["summary_sections"] = {"feature_doc": response.content}
        state["key_insights"] = [
            f"📦 {state['config'].get('feature_name', 'Feature')}",
            f"📊 {len(commits)} commits",
            f"👥 {len(contributor_stats)} contributors"
        ]
        
        print(f"✅ [SUMMARIZER] Generated feature documentation")
        
    except Exception as e:
        error_msg = f"Feature summarization failed: {str(e)}"
        print(f"❌ [SUMMARIZER] {error_msg}")
        state["errors"].append(error_msg)
    
    return state


# ============================================================================
# NODE 6: PUBLISHING
# ============================================================================

def publishing_node(state: AgentState) -> AgentState:
    """Format and export final document"""
    print("🔄 [PUBLISHING] Creating final document...")
    
    try:
        # Create output directory
        output_dir = Path("/tmp/doc_generator_output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{state['mode']}_{timestamp}.md"
        output_path = output_dir / filename
        
        # Build document
        document_parts = []
        
        # Header
        document_parts.append(f"# {state['mode'].replace('_', ' ').title()}")
        document_parts.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        document_parts.append(f"\nRepository: {state['repo_url']}")
        document_parts.append("\n---\n")
        
        # Key Insights
        if state.get("key_insights"):
            document_parts.append("## 📊 Key Insights\n")
            for insight in state["key_insights"]:
                document_parts.append(f"{insight}\n")
            document_parts.append("\n---\n")
        
        # Main content
        for section_name, content in state["summary_sections"].items():
            document_parts.append(f"\n## {section_name.replace('_', ' ').title()}\n")
            document_parts.append(content)
            document_parts.append("\n")
        
        # Metadata footer
        document_parts.append("\n---\n\n## 🔧 Generation Metadata\n")
        document_parts.append(f"- Mode: {state['mode']}\n")
        document_parts.append(f"- Commits Processed: {len(state.get('raw_commits', []))}\n")
        document_parts.append(f"- Repository: {state['repo_metadata'].get('name', 'Unknown')}\n")
        
        if state.get("warnings"):
            document_parts.append(f"\n### ⚠️  Warnings ({len(state['warnings'])})\n")
            for warning in state["warnings"]:
                document_parts.append(f"- {warning}\n")
        
        if state.get("errors"):
            document_parts.append(f"\n### ❌ Errors ({len(state['errors'])})\n")
            for error in state["errors"]:
                document_parts.append(f"- {error}\n")
        
        # Write to file
        final_doc = "\n".join(document_parts)
        output_path.write_text(final_doc, encoding='utf-8')
        
        state["final_document"] = final_doc
        state["output_path"] = str(output_path)
        
        print(f"✅ [PUBLISHING] Document saved to: {output_path}")
        print(f"   Size: {len(final_doc)} characters")
        
    except Exception as e:
        error_msg = f"Publishing failed: {str(e)}"
        print(f"❌ [PUBLISHING] {error_msg}")
        state["errors"].append(error_msg)
    
    return state


# ============================================================================
# BUILD WORKFLOW
# ============================================================================

def build_workflow() -> StateGraph:
    """Build and compile the LangGraph workflow"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("enhancement", enhancement_node)
    workflow.add_node("classification", classification_node)
    workflow.add_node("release_summarizer", release_summarizer_node)
    workflow.add_node("person_summarizer", person_summarizer_node)
    workflow.add_node("feature_summarizer", feature_summarizer_node)
    workflow.add_node("publishing", publishing_node)
    
    # Define flow
    workflow.set_entry_point("ingestion")
    workflow.add_edge("ingestion", "enhancement")
    workflow.add_edge("enhancement", "classification")
    
    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classification",
        router_node,
        {
            "release_summarizer": "release_summarizer",
            "person_summarizer": "person_summarizer",
            "feature_summarizer": "feature_summarizer"
        }
    )
    
    # All summarizers go to publishing
    workflow.add_edge("release_summarizer", "publishing")
    workflow.add_edge("person_summarizer", "publishing")
    workflow.add_edge("feature_summarizer", "publishing")
    
    # Publishing is the end
    workflow.add_edge("publishing", END)
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def generate_release_notes(repo_url: str, from_tag: str, to_tag: str):
    """Generate release notes between two tags"""
    
    print("\n" + "="*70)
    print("  AUTOMATED RELEASE NOTES GENERATOR")
    print("="*70 + "\n")
    
    app = build_workflow()
    
    initial_state = {
        "repo_url": repo_url,
        "mode": "release_notes",
        "config": {
            "from_tag": from_tag,
            "to_tag": to_tag
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
    
    result = app.invoke(initial_state, config={"configurable": {"thread_id": "release_notes_1"}})
    
    print("\n" + "="*70)
    print("  GENERATION COMPLETE")
    print("="*70 + "\n")
    print(f"Output: {result.get('output_path', 'N/A')}")
    print(f"Commits processed: {len(result.get('raw_commits', []))}")
    print(f"Errors: {len(result.get('errors', []))}")
    print(f"Warnings: {len(result.get('warnings', []))}")
    
    return result


# Example usage
if __name__ == "__main__":
    # Test with LangChain repository
    result = generate_release_notes(
        repo_url="https://github.com/langchain-ai/langchain",
        from_tag="v0.1.0",
        to_tag="v0.2.0"
    )
    
    print("\n📄 Preview of generated document:\n")
    print(result["final_document"][:500] + "...")

