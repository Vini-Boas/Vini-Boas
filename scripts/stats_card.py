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
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
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
rows = [
    ("Total de estrelas", stars),
    ("Commits (último ano)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
    ("Pull requests", user["pullRequests"]["totalCount"]),
    ("Issues", user["issues"]["totalCount"]),
    ("Contribuiu para", user["repositoriesContributedTo"]["totalCount"]),
]
title = f"Estatísticas de {user['name'] or user['login']}"

from html import escape  # noqa: E402

width = 360
height = 55 + len(rows) * 25 + 20
lines = "".join(
    f'<g transform="translate(25,{65 + i * 25})"><circle cx="5" cy="-4" r="4" class="dot"/>'
    f'<text x="18" class="stat">{escape(label)}</text>'
    f'<text x="{width - 50}" text-anchor="end" class="stat bold">{value:,}</text></g>'
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
@media (prefers-color-scheme: dark) {{
  .card {{ fill: #0d1117; stroke: #0d1117; }}
  .header {{ fill: #ebf1f7; }}
  .stat {{ fill: #ebf1f7; }}
}}
</style>
<rect class="card" x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}"/>
<text x="25" y="35" class="header">{escape(title)}</text>
{lines}
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(", ".join(f"{k}={v}" for k, v in rows))
