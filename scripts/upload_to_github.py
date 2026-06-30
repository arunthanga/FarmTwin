#!/usr/bin/env python3
"""Upload the restructured FarmTwin repo to GitHub via the REST API.

This script is meant to be run LOCALLY (not in Claude's sandbox — network
access to api.github.com is blocked there).

Prerequisites:
    pip install PyGithub requests

Usage:
    export GITHUB_TOKEN=ghp_your_token_here
    python scripts/upload_to_github.py

What it does:
    1. Reads every file in the repo root (relative paths)
    2. Creates or updates each file on GitHub via the Contents API
    3. Moves existing engine/docs files to the right place
    4. Reports success/failure per file

Safety: uses PUT /repos/{owner}/{repo}/contents/{path} which is idempotent
(creates if missing, updates if present using the file's current SHA).
"""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER        = "arunthanga"
REPO         = "FarmTwin"
BRANCH       = "master"
API_BASE     = f"https://api.github.com/repos/{OWNER}/{REPO}"

# Root of the local restructured repo (directory containing this script's parent)
REPO_ROOT = Path(__file__).parent.parent

# Files and directories to SKIP uploading (already on GitHub or not needed)
SKIP_PATHS = {
    "engine/docs/10-numerical-methods-and-architecture.md",
    "engine/docs/11-freecad-openfoam-twin-iitpkd-roadmap.md",
    "engine/docs/12-solver-mathematics.md",
    "engine/docs/13-sensors-and-instrumentation.md",
    "engine/docs/14-digital-twin-data-assimilation.md",
    "engine/docs/15-iitpkd-collaboration-brief.md",
    "engine/docs/16-annotated-bibliography.md",
    "engine/docs/17-weather-data-integration.md",
    "engine/docs/18-iot-control-architecture.md",
    "engine/docs/19-two-product-architecture.md",
    "engine/docs/20-design-optimization.md",
    "engine/docs/21-agronomy-layer.md",
    "engine/docs/22-implementation-whitepapers.md",
    ".git",
}

# ── Helpers ───────────────────────────────────────────────────────────

def gh_headers() -> dict:
    if not GITHUB_TOKEN:
        print("ERROR: set GITHUB_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_file_sha(remote_path: str) -> str | None:
    """Return the current SHA of a file on GitHub, or None if it doesn't exist."""
    url = f"{API_BASE}/contents/{remote_path}?ref={BRANCH}"
    r = requests.get(url, headers=gh_headers(), timeout=15)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def upload_file(local_path: Path, remote_path: str) -> bool:
    """Create or update a single file on GitHub. Returns True on success."""
    content = local_path.read_bytes()
    encoded = base64.b64encode(content).decode()

    sha = get_file_sha(remote_path)

    payload: dict = {
        "message": f"chore(restructure): add/update {remote_path}",
        "content": encoded,
        "branch":  BRANCH,
    }
    if sha:
        payload["sha"] = sha

    url = f"{API_BASE}/contents/{remote_path}"
    r = requests.put(url, headers=gh_headers(), json=payload, timeout=30)

    if r.status_code in (200, 201):
        action = "Updated" if sha else "Created"
        print(f"  ✓ {action}: {remote_path}")
        return True
    else:
        print(f"  ✗ FAILED {remote_path}: {r.status_code} {r.text[:120]}")
        return False


def collect_files() -> list[tuple[Path, str]]:
    """Collect (local_path, remote_path) pairs for all files to upload."""
    pairs = []
    for local in sorted(REPO_ROOT.rglob("*")):
        if not local.is_file():
            continue
        rel = local.relative_to(REPO_ROOT)
        remote = str(rel).replace("\\", "/")

        # Skip git internals and already-existing engine docs
        if any(remote.startswith(skip) or remote == skip for skip in SKIP_PATHS):
            continue
        if ".git/" in remote or remote.startswith(".git"):
            continue

        pairs.append((local, remote))
    return pairs


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    files = collect_files()
    print(f"\nFarmTwin GitHub Upload")
    print(f"  Repo:   {OWNER}/{REPO}  branch: {BRANCH}")
    print(f"  Files:  {len(files)} to upload\n")

    ok = 0
    fail = 0
    for local_path, remote_path in files:
        success = upload_file(local_path, remote_path)
        if success:
            ok += 1
        else:
            fail += 1
        # Respect GitHub API rate limit (5000 req/hour authenticated)
        time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"  Uploaded: {ok}   Failed: {fail}")
    if fail == 0:
        print("  ✓ All files uploaded successfully!")
        print(f"  View at: https://github.com/{OWNER}/{REPO}")
    else:
        print("  Some files failed — check errors above and retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
