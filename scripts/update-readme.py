#!/usr/bin/env python3
"""
Auto-updates the profile README with current public repos.
Runs daily via GitHub Actions.
"""

import json
import re
import urllib.request

USERNAME = "vivekptnk"
README_PATH = "README.md"

# Repos to exclude from the profile (forks, noise, etc.)
EXCLUDE = {"vivekptnk"}

# Optional: pin specific repos to the top with custom descriptions.
# If a repo is pinned here, it uses this description instead of the GitHub one.
# Order matters — pinned repos appear first.
PINNED = {
    # "RepoName": "Custom one-line description",
}


def fetch_public_repos():
    """Fetch all public repos for the user, sorted by last push."""
    url = f"https://api.github.com/users/{USERNAME}/repos?type=owner&sort=pushed&per_page=100"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req) as resp:
        repos = json.loads(resp.read().decode())

    results = []
    for r in repos:
        if r["fork"] or r["archived"] or r["name"] in EXCLUDE:
            continue
        name = r["name"]
        desc = PINNED.get(name, r.get("description") or "")
        lang = r.get("language") or ""
        url = r["html_url"]
        stars = r.get("stargazers_count", 0)
        results.append({
            "name": name,
            "description": desc,
            "language": lang,
            "url": url,
            "stars": stars,
            "pinned": name in PINNED,
        })

    # Pinned repos first (in PINNED order), then by push date (already sorted)
    pinned_order = list(PINNED.keys())
    results.sort(key=lambda r: (not r["pinned"], pinned_order.index(r["name"]) if r["pinned"] else 0))

    return results


def format_projects(repos):
    """Format repos into markdown for the README."""
    if not repos:
        return "> *Nothing here yet — projects will appear when they go public.*"

    lines = []
    for r in repos:
        lang_badge = f"`{r['language']}`" if r["language"] else ""
        star_str = f" | {'*' * r['stars']}{'star' if r['stars'] == 1 else 'stars'}" if r["stars"] > 0 else ""
        desc = f" — {r['description']}" if r["description"] else ""

        lines.append(f"**[{r['name']}]({r['url']})** {lang_badge}{desc}")

    return "\n\n".join(lines)


def update_readme(projects_md):
    """Replace content between PROJECTS markers."""
    with open(README_PATH, "r") as f:
        content = f.read()

    pattern = r"(<!-- PROJECTS:START -->)\n.*?\n(<!-- PROJECTS:END -->)"
    replacement = f"\\1\n{projects_md}\n\\2"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if new_content != content:
        with open(README_PATH, "w") as f:
            f.write(new_content)
        print(f"Updated README with {len(repos)} project(s).")
        return True
    else:
        print("No changes needed.")
        return False


if __name__ == "__main__":
    repos = fetch_public_repos()
    projects_md = format_projects(repos)
    update_readme(projects_md)
