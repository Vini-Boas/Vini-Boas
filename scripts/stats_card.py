"""Gera assets/stats.svg (um único SVG, claro/escuro) com as estatísticas do GitHub."""
import os
import sys

from common import env, fail, github

USER = env("GH_USER")
TOKEN = env("GH_TOKEN")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/stats.svg"

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    name
    login
    contributionsCollection { totalCommitContributions restrictedContributionsCount totalPullRequestReviewContributions }
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
  }
}"""


def gql(variables):
    data = github("https://api.github.com/graphql", TOKEN, {"query": QUERY, "variables": variables})
    if "errors" in data:
        fail(f"GraphQL: {data['errors']}")
    if not data["data"]["user"]:
        fail(f"Utilizador {USER!r} não encontrado.")
    return data["data"]["user"]


stars, cursor = 0, None
while True:
    user = gql({"login": USER, "cursor": cursor})
    stars += sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    page = user["repositories"]["pageInfo"]
    if not page["hasNextPage"]:
        break
    cursor = page["endCursor"]

cc = user["contributionsCollection"]
commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
prs, issues = user["pullRequests"]["totalCount"], user["issues"]["totalCount"]
reviews, followers = cc["totalPullRequestReviewContributions"], user["followers"]["totalCount"]
rows = [
    ("Total de estrelas", stars),
    ("Commits (último ano)", commits),
    ("Pull requests", prs),
    ("Issues", issues),
    ("Contribuiu para", user["repositoriesContributedTo"]["totalCount"]),
]


def rank_of():
    """Mesma fórmula do github-readme-stats: percentil ponderado -> nível S..C."""
    exp_cdf = lambda x: 1 - 2 ** -x
    log_cdf = lambda x: x / (1 + x)
    weights = 2 + 3 + 1 + 1 + 4 + 1
    score = (
        2 * exp_cdf(commits / 250)
        + 3 * exp_cdf(prs / 50)
        + 1 * exp_cdf(issues / 25)
        + 1 * exp_cdf(reviews / 2)
        + 4 * log_cdf(stars / 50)
        + 1 * log_cdf(followers / 10)
    )
    percentile = (1 - score / weights) * 100  # menor = melhor
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    limits = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    level = next(l for l, lim in zip(levels, limits) if percentile <= lim)
    return level, percentile


level, percentile = rank_of()
title = f"Estatísticas de {user['name'] or user['login']}"

from html import escape  # noqa: E402

width = 360
height = 55 + len(rows) * 25 + 20
import math  # noqa: E402

circ = 2 * math.pi * 36
ring = circ * max(0.05, (100 - percentile) / 100)
lines = "".join(
    f'<g transform="translate(25,{65 + i * 25})"><circle cx="5" cy="-4" r="4" class="dot"/>'
    f'<text x="18" class="stat">{escape(label)}</text>'
    f'<text x="235" text-anchor="end" class="stat bold">{value:,}</text></g>'
    for i, (label, value) in enumerate(rows)
)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="t">
<title id="t">{escape(title)}</title>
<style>
.card {{ fill: #ffffff; stroke: #d0d7de; }}
.header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #681c22; }}
.stat {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #1f2328; }}
.bold {{ font-weight: 700; }}
.dot {{ fill: #c7424b; }}
.track {{ stroke: #d0d7de; stroke-width: 6; fill: none; }}
.ring {{ stroke: #c7424b; stroke-width: 6; stroke-linecap: round; fill: none; }}
.rank {{ font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: #681c22; }}
@media (prefers-color-scheme: dark) {{
  .card {{ fill: #0d1117; stroke: #0d1117; }}
  .header {{ fill: #ebf1f7; }}
  .stat {{ fill: #ebf1f7; }}
  .track {{ stroke: #30363d; }}
  .ring {{ stroke: #D85C63; }}
  .rank {{ fill: #ebf1f7; }}
}}
</style>
<rect class="card" x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}"/>
<text x="25" y="35" class="header">{escape(title)}</text>
{lines}
<g transform="translate(300,110)">
<circle r="36" class="track"/>
<circle r="36" class="ring" stroke-dasharray="{ring:.1f} {circ:.1f}" transform="rotate(-90)"/>
<text y="9" text-anchor="middle" class="rank">{escape(level)}</text>
</g>
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(", ".join(f"{k}={v}" for k, v in rows), f"| reviews={reviews} followers={followers} rank={level} ({percentile:.1f}%)")
