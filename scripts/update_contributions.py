#!/usr/bin/env python3
"""Update the Open Source Contributions section in README.md using the GitHub API."""

from collections import OrderedDict
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "CarlosLopez-Ciber")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
README_PATH = Path(__file__).resolve().parent.parent / "README.md"

START_MARKER = "<!-- OSS-CONTRIBUTIONS:START -->"
END_MARKER = "<!-- OSS-CONTRIBUTIONS:END -->"


def fetch_merged_external_prs(username: str, token: str = "") -> list[dict]:
    """Fetch all merged pull requests authored by `username` in external repositories."""
    items: list[dict] = []
    query = f"is:pr is:merged author:{username} -user:{username}"
    encoded_query = urllib.parse.quote(query, safe="")
    page = 1

    while True:
        url = (
            f"https://api.github.com/search/issues"
            f"?q={encoded_query}&sort=updated&order=desc&per_page=100&page={page}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{username}-profile-readme-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        batch = data.get("items", [])
        items.extend(batch)

        if len(batch) < 100 or len(items) >= 1000:
            break
        page += 1

    return items


def build_section(prs: list[dict]) -> str:
    """Render the Markdown/HTML block for external open-source contributions."""
    if not prs:
        return "Aún no hay PRs fusionados en proyectos externos."

    repos: OrderedDict[str, list[dict]] = OrderedDict()
    for pr in prs:
        repo_api_url = pr.get("repository_url", "")
        repo_full_name = repo_api_url.split("/repos/", 1)[-1]
        repos.setdefault(repo_full_name, []).append(pr)

    lines: list[str] = []

    for repo_name, repo_prs in repos.items():
        repo_url = f"https://github.com/{repo_name}"
        count = len(repo_prs)
        count_label = "1 PR" if count == 1 else f"{count} PRs"
        escaped_repo = html.escape(repo_name)

        lines.append("<details>")
        lines.append(
            f'  <summary><b><a href="{repo_url}">{escaped_repo}</a></b> ({count_label})</summary>'
        )
        lines.append("  <ul>")
        for pr in sorted(repo_prs, key=lambda item: item["number"], reverse=True):
            number = pr["number"]
            title = html.escape(pr["title"].strip())
            pr_url = pr["html_url"]
            lines.append(f'    <li><a href="{pr_url}">#{number}</a> — {title}</li>')
        lines.append("  </ul>")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines).rstrip()


def update_readme(readme_path: Path, generated_block: str) -> bool:
    """Replace content between markers in README.md. Returns True if changed."""
    content = readme_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(START_MARKER)})(.*?)({re.escape(END_MARKER)})",
        flags=re.DOTALL,
    )
    if not pattern.search(content):
        raise RuntimeError(
            f"Markers {START_MARKER} / {END_MARKER} not found in {readme_path}"
        )

    replacement = f"{START_MARKER}\n{generated_block}\n{END_MARKER}"
    updated = pattern.sub(lambda _: replacement, content, count=1)

    if updated == content:
        return False

    readme_path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    prs = fetch_merged_external_prs(USERNAME, GITHUB_TOKEN)
    section = build_section(prs)
    changed = update_readme(README_PATH, section)
    print(f"Fetched {len(prs)} merged external PR(s). README updated: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
