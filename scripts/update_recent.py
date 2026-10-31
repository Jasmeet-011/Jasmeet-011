"""Rewrite the "Recently shipped" section of README.md with my latest commits.

Runs daily in GitHub Actions. Standard library only, no installs needed.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER = "Jasmeet-011"
MAX_ITEMS = 5
SKIP_REPOS = {USER}  # the profile repo itself
README = "README.md"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def ago(iso):
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - then).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    return f"{months} month{'s' if months > 1 else ''} ago"


def latest_commits():
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner")
    items = []
    for repo in repos:
        if repo["fork"] or repo["name"] in SKIP_REPOS:
            continue
        try:
            commits = api(f"/repos/{USER}/{repo['name']}/commits?author={USER}&per_page=1")
        except Exception:
            continue  # empty repo or API hiccup
        if not commits:
            continue
        c = commits[0]
        msg = c["commit"]["message"].splitlines()[0].strip().replace("`", "'")
        if len(msg) > 72:
            msg = msg[:69] + "..."
        items.append((c["commit"]["author"]["date"], repo["name"], repo["html_url"], msg))
    items.sort(reverse=True)
    return items[:MAX_ITEMS]


def main():
    lines = [
        f"- **[{name}]({url})** · `{msg}` · {ago(date)}"
        for date, name, url, msg in latest_commits()
    ]
    if not lines:
        return
    block = "<!--RECENT:START-->\n" + "\n".join(lines) + "\n<!--RECENT:END-->"
    with open(README) as f:
        text = f.read()
    text = re.sub(r"<!--RECENT:START-->.*?<!--RECENT:END-->", block, text, flags=re.S)
    with open(README, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
