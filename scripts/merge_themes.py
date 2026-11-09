"""Junta um cartão claro e um escuro num único SVG que segue o tema do visualizador.

Uso: merge_themes.py <dark.svg> <light.svg> <out.svg>

Cada cartão é embutido como imagem data: URI, o que o isola por completo
(sem colisão de classes CSS, ids ou animações entre os dois).
"""
import base64
import re
import sys

from common import fail


def load(path):
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        fail(f"Não foi possível ler {path}: {e}")
    text = raw.decode("utf-8", errors="replace")
    root = re.search(r"<svg\b[^>]*>", text)
    if not root:
        fail(f"{path} não é um SVG válido (tag <svg> não encontrada).")
    w = re.search(r'\bwidth="([\d.]+)', root.group(0))
    h = re.search(r'\bheight="([\d.]+)', root.group(0))
    if not (w and h):
        fail(f"{path}: <svg> sem width/height numéricos.")
    return base64.b64encode(raw).decode(), w.group(1), h.group(1)


def main():
    if len(sys.argv) != 4:
        fail("Uso: merge_themes.py <dark.svg> <light.svg> <out.svg>")
    dark, light, out = sys.argv[1:]
    d64, dw, dh = load(dark)
    l64, lw, lh = load(light)
    if (dw, dh) != (lw, lh):
        fail(f"Tamanhos diferentes: escuro {dw}x{dh}, claro {lw}x{lh}.")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{dw}" height="{dh}" viewBox="0 0 {dw} {dh}">
<style>
  .theme-dark {{ display: none; }}
  @media (prefers-color-scheme: dark) {{
    .theme-light {{ display: none; }}
    .theme-dark {{ display: inline; }}
  }}
</style>
<image class="theme-light" width="{lw}" height="{lh}" href="data:image/svg+xml;base64,{l64}"/>
<image class="theme-dark" width="{dw}" height="{dh}" href="data:image/svg+xml;base64,{d64}"/>
</svg>
'''
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{out} escrito ({len(svg)} bytes)")


main()
