#!/usr/bin/env python3
"""FarmTwin AI Code Review Bot.

Reads remaining Ruff issues + diff of changed files, calls the Anthropic API
to generate inline PR comments with:
  1. Explanation of the issue
  2. A code fix (if solvable automatically)
  3. A request for the developer (if fix requires domain knowledge)

Posts comments via the GitHub REST API.

Usage (called by CI):
    ANTHROPIC_API_KEY=... GITHUB_TOKEN=... PR_NUMBER=42 REPO=arunthanga/FarmTwin \
        python scripts/ai_code_review.py

Environment variables:
    ANTHROPIC_API_KEY   Anthropic API key (set in GitHub Actions secrets)
    GITHUB_TOKEN        GitHub token with pull-requests: write permission
    PR_NUMBER           Pull request number (set by CI)
    REPO                GitHub repository slug  (owner/repo)
    MAX_REVIEW_COMMENTS Max inline comments to post per run (default: 20)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

try:
    import anthropic
    from github import Github
    from github.PullRequest import PullRequest
except ImportError:
    print(
        "ERROR: Missing dependencies. Run: "
        "pip install anthropic pygithub",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("REPO", "")
PR_NUMBER = int(os.environ.get("PR_NUMBER", "0"))
MAX_COMMENTS = int(os.environ.get("MAX_REVIEW_COMMENTS", "20"))

# ── Helper: get changed Python files in the PR ────────────────────────────────

def get_changed_python_files() -> list[str]:
    """Return list of .py files changed in the current PR (via git diff)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/master...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in result.stdout.splitlines() if f.endswith(".py")]


def get_file_diff(filepath: str) -> str:
    """Return the unified diff for a single file vs master."""
    result = subprocess.run(
        ["git", "diff", "origin/master...HEAD", "--", filepath],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout[:4000]  # cap at 4 KB per file


def get_file_content(filepath: str, max_chars: int = 3000) -> str:
    """Return the first max_chars of a file, or empty string if not found."""
    path = Path(filepath)
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    return content[:max_chars]


def run_ruff_on_file(filepath: str) -> str:
    """Run Ruff on a single file and return its output."""
    result = subprocess.run(
        ["ruff", "check", filepath, "--output-format", "text"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


# ── AI Review ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are FarmTwin's AI code reviewer. FarmTwin is an agri digital-twin platform
    for precision irrigation in India. Its Python engine implements hydraulic solvers
    (GGA/Todini-Pilati), FAO-56 agronomy, and IoT control.

    Coding standards enforced:
    - Ruff (Python linter/formatter) — rules: E,W,F,I,N,UP,B,C4,C90,PL,PT,SIM,D,ANN,S
    - Physical variables MUST have unit suffixes: _m, _m3s, _lh, _pa, _kpa, _mmd, _mh, _c
    - Equations MUST cite the white-paper reference (author, year, eq. number)
    - No bare numeric literals for physical constants — use named constants
    - Every public function needs a Google-style docstring with Args/Returns/Raises
    - Type annotations required on all public functions

    For each Ruff issue provided:
    1. Briefly explain why it is a problem (1-2 sentences).
    2. Provide a FIXED version of the affected code block (Python, fenced).
    3. If the fix requires domain knowledge you cannot resolve (e.g., incorrect physics,
       wrong equation), write: "⚠️ DEVELOPER ACTION REQUIRED: <specific instruction>"

    Keep each response focused on the one issue. Do not repeat the Ruff rule ID in prose.
    Respond in plain GitHub Markdown.
""")


def ai_review_issue(
    filepath: str,
    ruff_issue: str,
    file_snippet: str,
    diff_snippet: str,
) -> str:
    """Call Claude API to review a single Ruff issue. Returns markdown comment."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ AI review skipped — ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_message = textwrap.dedent(f"""
        **File:** `{filepath}`

        **Ruff issue:**
        ```
        {ruff_issue}
        ```

        **Relevant file excerpt (first 3000 chars):**
        ```python
        {file_snippet}
        ```

        **PR diff for this file:**
        ```diff
        {diff_snippet}
        ```

        Please review this issue and provide (a) explanation, (b) fixed code or
        (c) DEVELOPER ACTION REQUIRED if you cannot fix it automatically.
    """)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text  # type: ignore[union-attr]


# ── GitHub PR Comment Posting ─────────────────────────────────────────────────

def parse_ruff_issues(ruff_output: str) -> list[dict]:
    """Parse Ruff text output into structured issue dicts.

    Ruff text format per line:
        path/to/file.py:LINE:COL: CODE Description
    """
    issues = []
    for line in ruff_output.splitlines():
        parts = line.split(":", 3)
        if len(parts) < 4:  # noqa: PLR2004
            continue
        filepath = parts[0].strip()
        if not filepath.endswith(".py"):
            continue
        try:
            line_no = int(parts[1])
            col = int(parts[2])
            message = parts[3].strip()
        except ValueError:
            continue
        issues.append({
            "filepath": filepath,
            "line": line_no,
            "col": col,
            "message": message,
        })
    return issues


def post_pr_comments(pr: PullRequest, issues: list[dict]) -> None:
    """Post AI-generated review comments to the PR."""
    commit = pr.get_commits().reversed[0]  # latest commit
    posted = 0

    for issue in issues:
        if posted >= MAX_COMMENTS:
            print(f"Reached max comments ({MAX_COMMENTS}); stopping.")
            break

        filepath = issue["filepath"]
        ruff_msg = issue["message"]
        line_no = issue["line"]

        file_content = get_file_content(filepath)
        diff = get_file_diff(filepath)

        print(f"AI reviewing: {filepath}:{line_no} — {ruff_msg[:60]}...")
        review_comment = ai_review_issue(filepath, ruff_msg, file_content, diff)

        # Format comment body
        body = textwrap.dedent(f"""
            **🤖 FarmTwin AI Code Review** — `{ruff_msg}`

            {review_comment}

            ---
            *Auto-generated by FarmTwin AI bot. If this fix is wrong, leave a comment
            mentioning `@farmtwin-bot ignore` to suppress future reviews for this line.*
        """).strip()

        try:
            pr.create_review_comment(
                body=body,
                commit=commit,
                path=filepath,
                line=line_no,
            )
            posted += 1
        except Exception as exc:  # noqa: BLE001
            # Review comments fail if the line is not in the diff; fall back to PR comment
            print(f"Inline comment failed ({exc}); posting as PR comment.")
            pr.create_issue_comment(
                f"**AI Review — `{filepath}:{line_no}`**\n\n{body}",
            )
            posted += 1


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the AI code review script."""
    if not GITHUB_TOKEN or not REPO or not PR_NUMBER:
        print("ERROR: GITHUB_TOKEN, REPO, and PR_NUMBER must be set.", file=sys.stderr)
        sys.exit(1)

    # Collect Ruff issues from changed files
    changed_files = get_changed_python_files()
    if not changed_files:
        print("No changed Python files found. Nothing to review.")
        return

    print(f"Changed Python files: {changed_files}")

    all_issues: list[dict] = []
    for filepath in changed_files:
        if not Path(filepath).exists():
            continue
        ruff_out = run_ruff_on_file(filepath)
        issues = parse_ruff_issues(ruff_out)
        all_issues.extend(issues)

    if not all_issues:
        print("No Ruff issues remaining after auto-fix. No AI review needed.")
        # Post a passing review
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(REPO)
        pr = repo.get_pull(PR_NUMBER)
        pr.create_review(
            body="✅ **FarmTwin AI Code Review**: No linting issues found. LGTM!",
            event="APPROVE",
        )
        return

    print(f"Found {len(all_issues)} Ruff issue(s) to review.")

    # Connect to GitHub and post comments
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO)
    pr = repo.get_pull(PR_NUMBER)

    post_pr_comments(pr, all_issues)

    # Post summary comment
    dev_actions = sum(
        1 for i in all_issues[:MAX_COMMENTS]
        if "DEVELOPER ACTION REQUIRED" in i.get("message", "")
    )
    auto_fixed = len(all_issues) - dev_actions
    summary = textwrap.dedent(f"""
        ## 🤖 FarmTwin AI Code Review Summary

        | | Count |
        |---|---|
        | Ruff issues found | {len(all_issues)} |
        | Auto-fixable (Ruff --fix applied) | {auto_fixed} |
        | Requires developer action | {dev_actions} |

        Inline review comments posted above. Please address **DEVELOPER ACTION REQUIRED**
        items before merging.
    """).strip()
    pr.create_issue_comment(summary)

    print("AI code review complete.")
    # Exit 0 even if there are issues — CI pass/fail is controlled by Ruff check job
    sys.exit(0)


if __name__ == "__main__":
    main()
