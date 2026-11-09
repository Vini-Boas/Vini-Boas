"""Helpers partilhados: erros explícitos e chamadas à API do GitHub."""
import json
import os
import sys
import urllib.error
import urllib.request


def fail(msg):
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"Variável de ambiente {name} não definida ou vazia.")
    return value


def github(url, token, body=None):
    headers = {
        "Authorization": f"bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-workflow",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        fail(f"{url} -> HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        fail(f"{url} -> {e.reason}")
