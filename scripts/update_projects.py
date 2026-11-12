"""Gera um cartão SVG por projeto e idioma e atualiza a lista nos READMEs.

- pt: assets/cards/<org>.svg (README.md); en: assets/cards/en/<org>.svg (README.en.md).

- Logo: assets/logos/<org>.svg se existir, senão o avatar da própria org.
- Commits: total de commits do utilizador em repositórios da org (search API).
- Os cartões são imagens de largura fixa dentro de um <p>, por isso quebram
  naturalmente de linha conforme a largura do ecrã (sem tabela).
"""
import base64
import json
import re
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

from common import env, fail, github

ROOT = Path(__file__).resolve().parent.parent
# idioma -> (README, pasta dos cartões, chave da tagline em projects.json)
LANGS = {
    "pt": (ROOT / "README.md", "assets/cards", "tagline"),
    "en": (ROOT / "README.en.md", "assets/cards/en", "tagline_en"),
}
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"
CARD_W, CARD_H, LOGO = 400, 120, 80

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


def logo_data_uri(org):
    local = ROOT / "assets" / "logos" / f"{org}.svg"
    if local.exists():
        return "data:image/svg+xml;base64," + base64.b64encode(local.read_bytes()).decode()
    url = f"https://github.com/{org}.png?size=160"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return "data:image/png;base64," + base64.b64encode(r.read()).decode()
    except (urllib.error.URLError, OSError) as e:
        fail(f"Sem logo em assets/logos/{org}.svg e não foi possível baixar o avatar ({url}): {e}")


def card_svg(p, tagline, n_commits):
    org = escape(p["org"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" fill="none" role="img" aria-labelledby="t">
<title id="t">{org}</title>
<style>
.card {{ fill: #ffffff; stroke: #d0d7de; }}
.name {{ font: 600 17px 'Segoe UI', Ubuntu, Sans-Serif; fill: #681c22; }}
.line {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #1f2328; }}
.commits {{ font: 600 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c7424b; }}
@media (prefers-color-scheme: dark) {{
  .card {{ fill: #0d1117; stroke: #30363d; }}
  .name {{ fill: #ebf1f7; }}
  .line {{ fill: #ebf1f7; }}
  .commits {{ fill: #D85C63; }}
}}
</style>
<rect class="card" x="0.5" y="0.5" rx="6" width="{CARD_W - 1}" height="{CARD_H - 1}"/>
<image x="20" y="{(CARD_H - LOGO) // 2}" width="{LOGO}" height="{LOGO}" preserveAspectRatio="xMidYMid meet" href="{logo_data_uri(p['org'])}"/>
<text x="120" y="38" class="name">{org}</text>
<text x="120" y="60" class="line">{escape(tagline)}</text>
<text x="120" y="78" class="line">{escape(p['tags'])}</text>
<text x="120" y="99" class="commits">{n_commits} commits</text>
</svg>
"""


counts = {p["org"]: commits(p["org"]) for p in projects}
pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

for readme, cards_dir, key in LANGS.values():
    (ROOT / cards_dir).mkdir(parents=True, exist_ok=True)
    items = []
    for p in projects:
        org = p["org"]
        svg = card_svg(p, p[key], counts[org])
        (ROOT / cards_dir / f"{org}.svg").write_text(svg, encoding="utf-8")
        items.append(
            f'  <a href="https://github.com/{org}"><img src="./{cards_dir}/{org}.svg" '
            f'width="{CARD_W}" alt="{escape(org)}"/></a>'
        )
    block = '<p align="center">\n' + "\n".join(items) + "\n</p>"
    text = readme.read_text(encoding="utf-8")
    if not pattern.search(text):
        fail(f"{readme.name} não tem os marcadores {START} / {END}.")
    readme.write_text(pattern.sub(lambda _: f"{START}\n{block}\n{END}", text), encoding="utf-8")

print(f"{len(projects)} cartões gerados por idioma")
