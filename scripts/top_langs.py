import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "assets"
MAX_LANGS = 8
EXCLUDE = {"HTML", "CSS", "Jupyter Notebook", "Dockerfile", "Shell", "Batchfile"} - set(
    os.environ.get("KEEP_LANGS", "").split(",")
)

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositoriesContributedTo(first: 100, after: $cursor, includeUserRepositories: true,
      contributionTypes: [COMMIT, PULL_REQUEST]) {
      pageInfo { hasNextPage endCursor }
      nodes { isFork languages(first: 20) { edges { size node { name color } } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { languages(first: 20) { edges { size node { name color } } } }
    }
  }
}"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


totals, colors, seen = {}, {}, 0
cursor, owned_done = None, False
while True:
    user = gql({"login": USER, "cursor": cursor})
    repos = [n for n in user["repositoriesContributedTo"]["nodes"] if not n["isFork"]]
    if not owned_done:
        repos += user["repositories"]["nodes"]
        owned_done = True
    for repo in repos:
        seen += 1
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name in EXCLUDE:
                continue
            totals[name] = totals.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or "#858585"
    page = user["repositoriesContributedTo"]["pageInfo"]
    if not page["hasNextPage"]:
        break
    cursor = page["endCursor"]

top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:MAX_LANGS]
total = sum(v for _, v in top) or 1
langs = [(n, v / total * 100) for n, v in top]

THEMES = {
    "dark": dict(title="#ebf1f7", text="#ebf1f7", bg="#0d1117", border="#0d1117"),
    "light": dict(title="#681c22", text="#1f2328", bg="#ffffff", border="#d0d7de"),
}

def render(t):
    width, bar_w = 300, 250
    rows = (len(langs) + 1) // 2
    height = 90 + rows * 25
    bar, x = [], 0.0
    for name, pct in langs:
        w = bar_w * pct / 100
        bar.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{colors[name]}"/>')
        x += w
    legend = []
    for i, (name, pct) in enumerate(langs):
        col, row = i % 2, i // 2
        lx, ly = col * 150, row * 25
        legend.append(
            f'<g transform="translate({lx},{ly})"><circle cx="5" cy="6" r="5" fill="{colors[name]}"/>'
            f'<text x="15" y="10" class="lang">{escape(name)} {pct:.2f}%</text></g>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="t">
<title id="t">Linguagens mais usadas</title>
<style>
.header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {t['title']}; }}
.lang {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {t['text']}; }}
</style>
<rect x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}" fill="{t['bg']}" stroke="{t['border']}"/>
<text x="25" y="35" class="header">Linguagens mais usadas</text>
<g transform="translate(25,55)"><mask id="m"><rect width="{bar_w}" height="8" rx="5" fill="white"/></mask>
<g mask="url(#m)">{''.join(bar)}</g></g>
<g transform="translate(25,80)">{''.join(legend)}</g>
</svg>"""

os.makedirs(OUT_DIR, exist_ok=True)
for mode, theme in THEMES.items():
    with open(os.path.join(OUT_DIR, f"top-langs-{mode}.svg"), "w") as f:
        f.write(render(theme))
print(f"{seen} repos analysed; top: {', '.join(n for n, _ in langs)}")