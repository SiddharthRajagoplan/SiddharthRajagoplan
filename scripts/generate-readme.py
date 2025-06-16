import os, yaml, requests, jinja2, feedparser
from datetime import datetime, timedelta
from collections import Counter

GH_API = "https://api.github.com"

cfg = yaml.safe_load(open("config.yml"))
template = jinja2.Template(open("README.template.md").read())

user = os.getenv("GH_USER")
token = os.getenv("GH_TOKEN")
headers = {"Authorization": f"bearer {token}"} if token else {}

# -------------- helpers ----------------

def gh(path):
    """Thin GitHub REST wrapper"""
    return requests.get(f"{GH_API}{path}", headers=headers).json()


def weekly_stats():
    since = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
    events = gh(f"/users/{user}/events?per_page=300")
    prs = [e for e in events if e["type"] == "PullRequestEvent"
           and e["payload"]["pull_request"].get("merged_at")
           and e["payload"]["pull_request"]["merged_at"] >= since]
    issues = [e for e in events if e["type"] == "IssuesEvent" and e["payload"]["action"] == "closed"]
    return len(prs), len(issues)


def top_languages(n=5):
    repos = gh(f"/users/{user}/repos?per_page=100&sort=pushed")
    counter = Counter()
    for r in repos:
        if r.get("fork"):
            continue
        lang = r.get("language")
        if lang:
            counter[lang] += 1
    langs = [l for l, _ in counter.most_common(n)]
    return ", ".join(langs) if langs else "N/A"


SHIELD_STYLE = "for-the-badge&logo="
BADGE_MAP = {
    "python": "python",
    "pytorch": "pytorch",
    "kubernetes": "kubernetes",
    "rust": "rust",
    "langchain": "openai",
    "neo4j": "neo4j",
}


def make_badges(keys):
    parts = []
    for key in keys:
        logo = BADGE_MAP.get(key.lower(), "")
        url = f"https://img.shields.io/badge/-{key.capitalize()}-000?style={SHIELD_STYLE}{logo}"
        parts.append(f"![{key}]({url})")
    return " ".join(parts)


def latest_blog(rss, n=3):
    if not rss:
        return "*(RSS not configured)*"
    feed = feedparser.parse(rss)
    items = feed.entries[:n]
    lines = [f"- {datetime(*e.published_parsed[:3]).strftime('%Y-%m-%d')} – [{e.title}]({e.link})" for e in items]
    return "\n".join(lines) or "*(No posts yet)*"


def bullet(items):
    return "\n".join(f"- {i}" for i in items)


prs, closed_issues = weekly_stats()
metrics_table = (
    "| PRs merged | Issues closed | Top Languages |\n"
    "|------------|---------------|---------------|\n"
    f"| {prs} | {closed_issues} | {top_languages(cfg.get('metrics', {}).get('top_languages', 5))} |"
)

context = {
    **cfg,
    "user": user,
    "badges": make_badges(cfg.get("badges", [])),
    "metrics_table": metrics_table,
    "blog_links": latest_blog(cfg.get("blog_rss")),
    "current_projects": bullet(cfg.get("current_projects", [])),
}

with open("README.md", "w") as f:
    f.write(template.render(**context))