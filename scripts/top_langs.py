"""Gera assets/top-langs.svg (um único SVG, claro/escuro) com as linguagens mais usadas,
incluindo repositórios de organizações em que o utilizador contribuiu.

Os bytes de cada linguagem em cada repo são ponderados pela fração de commits do
utilizador nesse repo (meus commits / commits totais, na branch padrão)."""
import os
import sys
from html import escape

from common import env, fail, github

USER = env("GH_USER")
TOKEN = env("GH_TOKEN")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/top-langs.svg"
MAX_LANGS = 8
EXCLUDE = {"HTML", "CSS", "Jupyter Notebook", "Dockerfile", "Shell", "Batchfile"} - {
    x for x in os.environ.get("KEEP_LANGS", "").split(",") if x
}

QUERY = """
fragment R on Repository {
  nameWithOwner
  isFork
  languages(first: 20) { edges { size node { name color } } }
  defaultBranchRef { target { ... on Commit {
    total: history { totalCount }
    mine: history(author: {id: $id}) { totalCount }
  } } }
}
query($login: String!, $id: ID!, $cursor: String) {
  user(login: $login) {
    repositoriesContributedTo(first: 100, after: $cursor, includeUserRepositories: true,
      contributionTypes: [COMMIT, PULL_REQUEST]) {
      pageInfo { hasNextPage endCursor }
      nodes { ...R }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { ...R }
    }
  }
}"""


def gql(query, variables):
    data = github("https://api.github.com/graphql", TOKEN, {"query": query, "variables": variables})
    if "errors" in data:
        fail(f"GraphQL: {data['errors']}")
    return data["data"]


me = gql("query($l: String!) { user(login: $l) { id } }", {"l": USER})["user"]
if not me:
    fail(f"Utilizador {USER!r} não encontrado.")
USER_ID = me["id"]

# Cada repo contribui com (bytes por linguagem) x (meus commits / commits totais do repo).
totals, colors, seen, visited = {}, {}, 0, set()
cursor, owned_done = None, False
while True:
    user = gql(QUERY, {"login": USER, "id": USER_ID, "cursor": cursor})["user"]
    repos = [n for n in user["repositoriesContributedTo"]["nodes"] if not n["isFork"]]
    if not owned_done:
        repos += user["repositories"]["nodes"]
        owned_done = True
    for repo in repos:
        name_ = repo["nameWithOwner"]
        if name_ in visited:
            continue
        visited.add(name_)
        seen += 1
        branch = repo["defaultBranchRef"]
        if not branch or not branch["target"]:
            print(f"  {name_}: sem branch padrão (vazio), ignorado")
            continue
        mine, total_c = branch["target"]["mine"]["totalCount"], branch["target"]["total"]["totalCount"]
        weight = mine / total_c if total_c else 0
        langs_ = [f'{e["node"]["name"]}={e["size"]}' for e in repo["languages"]["edges"]]
        print(f"  {name_}: {mine}/{total_c} commits ({weight:.0%}) | {', '.join(langs_) or '(sem linguagens)'}")
        for e in repo["languages"]["edges"]:
            lang = e["node"]["name"]
            if lang in EXCLUDE:
                continue
            totals[lang] = totals.get(lang, 0) + e["size"] * weight
            colors[lang] = e["node"]["color"] or "#858585"
    page = user["repositoriesContributedTo"]["pageInfo"]
    if not page["hasNextPage"]:
        break
    cursor = page["endCursor"]

if not totals or sum(totals.values()) == 0:
    fail(
        f"Nenhum commit seu encontrado em {seen} repositórios. Ou o token não tem acesso, "
        "ou os commits não estão associados à sua conta GitHub (email não verificado)."
    )

top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:MAX_LANGS]
total = sum(v for _, v in top)
langs = [(n, v / total * 100) for n, v in top]


def render():
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
        lx, ly = (i % 2) * 150, (i // 2) * 25
        legend.append(
            f'<g transform="translate({lx},{ly})"><circle cx="5" cy="6" r="5" fill="{colors[name]}"/>'
            f'<text x="15" y="10" class="lang">{escape(name)} {pct:.2f}%</text></g>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="t">
<title id="t">Linguagens mais usadas</title>
<style>
.card {{ fill: #ffffff; stroke: #d0d7de; }}
.header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #681c22; }}
.lang {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #1f2328; }}
@media (prefers-color-scheme: dark) {{
  .card {{ fill: #0d1117; stroke: #0d1117; }}
  .header {{ fill: #ebf1f7; }}
  .lang {{ fill: #ebf1f7; }}
}}
</style>
<rect class="card" x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}"/>
<text x="25" y="35" class="header">Linguagens mais usadas</text>
<g transform="translate(25,55)"><mask id="m"><rect width="{bar_w}" height="8" rx="5" fill="white"/></mask>
<g mask="url(#m)">{''.join(bar)}</g></g>
<g transform="translate(25,80)">{''.join(legend)}</g>
</svg>
"""


os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(render())
print(f"{seen} repos analisados; top: {', '.join(n for n, _ in langs)}")
