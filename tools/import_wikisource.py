#!/usr/bin/env python3
"""Convertit le HTML rendu d'une page « Texte entier » de Wikisource en Markdown.

Usage : python3 tools/import_wikisource.py ENTIER.json SORTIE_DIR

ENTIER.json = réponse de l'API MediaWiki (action=parse&prop=text&formatversion=2).
Produit un fichier Markdown par section (titre h2/h3), sans interpréter les titres :
le chapitrage final (noms de fichiers, titres) est décidé ensuite à la main.

Conventions : paragraphes séparés par une ligne vide, italiques en *…*,
coquilles corrigées par Wikisource conservées sous leur forme corrigée,
numéros de page de l'édition papier supprimés, retours à la ligne de composition aplatis.
"""
import html
import json
import re
import sys
from pathlib import Path


def _emph(inner):
    core = inner.strip()
    if not core:
        return inner
    lead = " " if inner[:1] == " " else ""
    trail = " " if inner[-1:] == " " else ""
    return f"{lead}*{core}*{trail}"


def clean_inline(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S)
    # numéros de page de l'édition papier
    s = re.sub(r'<span><span class="pagenum[^"]*"[^>]*></span></span>', " ", s)
    s = re.sub(r'<span class="pagenum[^"]*"[^>]*></span>', " ", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    # abréviations : on garde <abbr> et <sup> (HTML en ligne accepté par Markdown)
    s = re.sub(r'<abbr class="abbr" title="([^"]*)">', r'<abbr title="\1">', s)
    s = re.sub(r'<sup style="[^"]*">', "<sup>", s)
    # spans de mise en forme : on garde le texte
    s = re.sub(r'<span class="(?:lang-la|coquille|romain|sc)"[^>]*>(.*?)</span>', r"\1", s, flags=re.S)
    s = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", s, flags=re.S)
    s = re.sub(r"<span[^>]*></span>", "", s)
    # italiques : on déplace les espaces en dehors des marqueurs, puis on fusionne
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    s = re.sub(r"<i>(.*?)</i>", lambda m: _emph(m.group(1)), s, flags=re.S)
    s = re.sub(r"\*( ?)\*", r"\1", s)  # « *a* *b* » -> « *a b* »
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


def paragraphs(fragment):
    out = []
    for m in re.finditer(r'<(p|div)([^>]*)>(.*?)</\1>', fragment, re.S):
        tag, attrs, inner = m.groups()
        text = clean_inline(re.sub(r"</?div[^>]*>|</?p[^>]*>", " ", inner))
        if not text:
            continue
        if tag == "div" and "text-align:right" in attrs:
            out.append(f'<p class="signature">{text}</p>')
        else:
            out.append(text)
    return out


def main(src, outdir):
    t = json.load(open(src, encoding="utf-8"))["parse"]["text"]
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    heads = list(re.finditer(r"<h([23])[^>]*>(.*?)</h\1>", t, re.S))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
        title = re.sub(r"<[^>]+>|\s+", " ", h.group(2)).strip()
        body = "\n\n".join(paragraphs(t[h.end():end]))
        name = f"{i:02d}.md"
        (outdir / name).write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        print(name, title, len(body))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
