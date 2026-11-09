"""Regenera a tabela de projetos do README a partir de scripts/projects.json.

- Imagem: assets/<org>.svg se existir, senão o avatar da própria org.
- Commits: total de commits do utilizador em repositórios da org (search API).
"""
import json
import re
import sys
from html import escape
from pathlib import Path

from common import env, fail, github

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"
COLUMNS = 3

user, token = env("GH_USER"), env("GH_TOKEN")
projects = json.loads((ROOT / "scripts" / "projects.json").read_text(encoding="utf-8"))


def commits(org):
    data = github(
        f"https://api.github.com/search/commits?q=author:{user}+org:{org}&per_page=1", token
    )
    total = data["total_count"]
    if total == 0:
        fail(
            f"0 commits de {user} na org {org}. Ou o utilizador/org está errado, ou o token "
            "STATS_TOKEN não tem acesso aos repositórios (precisa do scope 'repo')."
        )
    return total


def cell(p):
    org = p["org"]
    asset = ROOT / "assets" / f"{org}.svg"
    src = f"./assets/{org}.svg" if asset.exists() else f"https://github.com/{org}.png"
    return (
        '    <td align="center" width="180">\n'
        f'      <a href="https://github.com/{org}"><img src="{src}" height="56" alt="{escape(org)}"/>'
        f"<br/><b>{escape(org)}</b></a><br/>\n"
        f'      <sub>{escape(p["tagline"])}</sub><br/>\n'
        f'      <sub>{escape(p["tags"])}</sub><br/>\n'
        f"      <sub>{commits(org)} commits</sub>\n"
        "    </td>\n"
    )


rows = []
for i in range(0, len(projects), COLUMNS):
    chunk = projects[i : i + COLUMNS]
    rows.append("  <tr>\n" + "".join(cell(p) for p in chunk) + "  </tr>\n")
table = f"<table>\n{''.join(rows)}</table>"

text = README.read_text(encoding="utf-8")
pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
if not pattern.search(text):
    fail(f"README.md não tem os marcadores {START} / {END}.")
README.write_text(pattern.sub(lambda _: f"{START}\n{table}\n{END}", text), encoding="utf-8")
print(f"{len(projects)} projetos atualizados")
