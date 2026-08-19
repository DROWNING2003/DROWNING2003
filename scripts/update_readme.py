#!/usr/bin/env python3
"""Update the profile README with recent public GitHub activity."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

USERNAME = "DROWNING2003"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path(__file__).resolve().parent.parent / "README.md"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "DROWNING2003-profile-readme",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def request_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{url}: HTTP {error.code} {error.reason}") from error


def recent_repositories(cutoff: datetime) -> list[dict[str, Any]]:
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=pushed"
    repositories = request_json(url)
    activity: list[dict[str, Any]] = []
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    for repository in repositories:
        if repository["fork"] or repository["name"].lower() == USERNAME.lower():
            continue
        pushed_at = repository.get("pushed_at")
        if not pushed_at or pushed_at < cutoff_iso:
            continue

        commits_url = f"{repository['url']}/commits?since={urllib.parse.quote(cutoff_iso)}&per_page=100"
        try:
            commits = request_json(commits_url)
        except RuntimeError as error:
            print(f"Skipping {repository['full_name']}: {error}")
            continue
        if not commits:
            continue

        releases = request_json(f"{repository['url']}/releases?per_page=1")
        release = releases[0] if releases and releases[0].get("published_at", "") >= cutoff_iso else None
        activity.append(
            {
                "kind": "repository",
                "name": repository["name"],
                "url": repository["html_url"],
                "count": len(commits),
                "count_is_lower_bound": len(commits) == 100,
                "release": release,
                "time": pushed_at,
            }
        )

    return activity


def merged_contributions(cutoff: datetime) -> list[dict[str, Any]]:
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    query = f"author:{USERNAME} type:pr is:merged merged:>={cutoff_date}"
    url = "https://api.github.com/search/issues?per_page=100&sort=updated&order=desc&q=" + urllib.parse.quote(query)
    pulls = request_json(url).get("items", [])
    repositories: dict[str, dict[str, Any]] = {}

    for pull in pulls:
        repository_url = pull["repository_url"]
        full_name = repository_url.removeprefix("https://api.github.com/repos/")
        owner = full_name.split("/", 1)[0]
        if owner.lower() == USERNAME.lower():
            continue
        current = repositories.setdefault(
            full_name,
            {
                "kind": "contribution",
                "name": full_name,
                "url": f"https://github.com/{full_name}",
                "count": 0,
                "time": pull["updated_at"],
            },
        )
        current["count"] += 1
        current["time"] = max(current["time"], pull["updated_at"])

    return list(repositories.values())


def markdown(items: list[dict[str, Any]]) -> str:
    if not items:
        return "_No public activity in this period._"

    lines: list[str] = []
    for item in sorted(items, key=lambda value: value["time"], reverse=True)[:10]:
        if item["kind"] == "contribution":
            label = "PR" if item["count"] == 1 else "PRs"
            lines.append(f"- [{item['name']}]({item['url']}) ({item['count']} merged {label})")
            continue

        count = f"{item['count']}+" if item.get("count_is_lower_bound") else str(item["count"])
        details = [f"{count} commits"]
        release = item.get("release")
        if release:
            details.append(f"[{release['tag_name']}]({release['html_url']})")
        lines.append(f"- [{item['name']}]({item['url']}) ({', '.join(details)})")
    return "\n".join(lines)


def replace_section(content: str, name: str, value: str) -> str:
    start = f"<!-- {name}_START -->"
    end = f"<!-- {name}_END -->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    replacement = f"{start}\n{value}\n{end}"
    updated, count = pattern.subn(replacement, content)
    if count != 1:
        raise RuntimeError(f"README must contain exactly one {name} marker pair")
    return updated


def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    try:
        items = recent_repositories(cutoff) + merged_contributions(cutoff)
    except (RuntimeError, urllib.error.URLError) as error:
        raise SystemExit(f"GitHub API request failed: {error}") from error

    content = README.read_text(encoding="utf-8")
    content = replace_section(content, "ACTIVITY", markdown(items))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = replace_section(content, "UPDATED", f"_Last updated: {timestamp}_")
    README.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
