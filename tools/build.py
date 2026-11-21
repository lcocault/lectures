#!/usr/bin/env python3
"""Génère le site statique (site/) à partir de content/.

Usage : .venv/bin/python tools/build.py [--root DIR]

Entrées  : config.yaml, content/<slug>/book.yaml, chapitres/*.md, notes/*.md
Sorties  : site/index.html, site/data/library.json,
           site/<slug>/index.html, site/<slug>/book.json, site/<slug>/<chapitre>.html
Les fichiers site/assets/ sont conservés tels quels (CSS/JS à la main).
"""
import argparse
import html
import json
import re
import shutil
from pathlib import Path

import markdown
import yaml

NOTE_TYPES = {
    "geographie": "Géographie",
    "histoire": "Histoire",
    "philosophie": "Philosophie",
    "litterature": "Littérature",
    "vocabulaire": "Vocabulaire",
    "personnage": "Personnage",
    "culture": "Culture et société",
}


def split_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def md(text):
    return markdown.markdown(text, extensions=["extra", "smarty"], output_format="html5")


def esc(s):
    return html.escape(str(s), quote=True)


def render_paragraphs(body):
    """Rend le Markdown d'un chapitre en donnant un id stable (p1, p2…) à chaque paragraphe.

    Les ids suivent l'ordre des blocs de texte (séparés par une ligne vide) ;
    les notes s'y ancrent via `ancrage: p3`.
    """
    out, n = [], 0
    for block in re.split(r"\n\s*\n", body.strip()):
        rendered = md(block)
        if block.lstrip().startswith(("#", ">", "-", "*", "1.")) or not rendered.startswith("<p>"):
            out.append(rendered)
            continue
        n += 1
        out.append(rendered.replace("<p>", f'<p id="p{n}">', 1))
    return "\n".join(out), n


def page(cfg, title, body, depth, extra_head=""):
    up = "../" * depth
    lic = cfg["content_license"]
    return f"""<!doctype html>
<html lang="{esc(cfg['lang'])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}assets/style.css">
{extra_head}
</head>
<body>
<header class="site-header"><a href="{up}index.html">{esc(cfg['site_title'])}</a></header>
<main>
{body}
</main>
<footer class="site-footer">Contenu éditorial (chapitrage, notes) sous
<a href="{esc(lic['url'])}">{esc(lic['name'])}</a>.</footer>
<script src="{up}assets/app.js" defer></script>
</body>
</html>
"""


def load_notes(book_dir):
    notes = []
    for f in sorted((book_dir / "notes").glob("*.md")):
        meta, body = split_front_matter(f.read_text(encoding="utf-8"))
        meta.setdefault("id", f.stem)
        meta.setdefault("type", "culture")
        meta["_html"] = md(body)
        notes.append(meta)
    return notes


def render_note(n):
    sources = ""
    if n.get("sources"):
        items = "".join(
            f'<li><a href="{esc(s["url"])}">{esc(s.get("titre", s["url"]))}</a>'
            f'{" — " + esc(s["licence"]) if s.get("licence") else ""}</li>'
            for s in n["sources"]
        )
        sources = f'<footer class="note-sources"><strong>Sources</strong><ul>{items}</ul></footer>'
    resume = f'<p class="note-resume">{esc(n["resume"])}</p>' if n.get("resume") else ""
    detail = ""
    if n["_html"].strip():
        detail = f'<details class="note-detail"><summary>Pour aller plus loin</summary>{n["_html"]}{sources}</details>'
    elif sources:
        detail = sources
    label = NOTE_TYPES.get(n["type"], n["type"])
    return (
        f'<aside class="note" id="note-{esc(n["id"])}" data-type="{esc(n["type"])}">'
        f'<h3>{esc(n["titre"])} <span class="note-type">{esc(label)}</span></h3>{resume}{detail}</aside>'
    )


def build_book(root, cfg, out, slug):
    book_dir = root / "content" / slug
    book = yaml.safe_load((book_dir / "book.yaml").read_text(encoding="utf-8"))
    notes = load_notes(book_dir)
    base = cfg.get("audio_base_url", "").rstrip("/")
    book_out = out / slug
    if book_out.exists():
        shutil.rmtree(book_out)
    book_out.mkdir(parents=True)

    chapters = []
    for f in sorted((book_dir / "chapitres").glob("*.md")):
        meta, body = split_front_matter(f.read_text(encoding="utf-8"))
        chapters.append({"id": f.stem, "title": meta.get("titre", f.stem), "meta": meta, "body": body})

    chapter_notes = {c["id"]: [n for n in notes if n.get("chapitre") == c["id"]] for c in chapters}

    for i, c in enumerate(chapters):
        content, _ = render_paragraphs(c["body"])
        anchors = {}
        for n in chapter_notes[c["id"]]:
            anchors.setdefault(n.get("ancrage"), []).append(n)
        # insère un marqueur de note à la fin du paragraphe ancré
        for pid, ns in anchors.items():
            if not pid:
                continue
            marks = "".join(
                f' <a class="note-ref" href="#note-{esc(n["id"])}" title="{esc(n["titre"])}">[note]</a>' for n in ns
            )
            content = re.sub(rf'(<p id="{re.escape(pid)}">.*?)(</p>)', lambda m: m.group(1) + marks + m.group(2), content, count=1, flags=re.S)

        audio = ""
        if base and c["meta"].get("audio", book.get("audio", False)):
            audio = f'<audio controls preload="none" src="{esc(base)}/{esc(slug)}/{esc(c["id"])}.mp3"></audio>'
        prev_l = f'<a rel="prev" href="{chapters[i-1]["id"]}.html">← {esc(chapters[i-1]["title"])}</a>' if i else "<span></span>"
        next_l = f'<a rel="next" href="{chapters[i+1]["id"]}.html">{esc(chapters[i+1]["title"])} →</a>' if i + 1 < len(chapters) else "<span></span>"
        notes_html = "".join(render_note(n) for n in chapter_notes[c["id"]])
        body_html = (
            f'<nav class="crumbs"><a href="index.html">{esc(book["titre"])}</a></nav>'
            f'<article class="chapter"><h1>{esc(c["title"])}</h1>{audio}{content}</article>'
            f'<nav class="pager">{prev_l}{next_l}</nav>'
            f'<section class="notes" aria-label="Notes"><h2>Notes</h2>{notes_html or "<p>Aucune note pour ce chapitre.</p>"}</section>'
        )
        (book_out / f'{c["id"]}.html').write_text(
            page(cfg, f'{c["title"]} — {book["titre"]}', body_html, 1), encoding="utf-8")

    # page du livre : sommaire + index des notes par type
    toc = "".join(f'<li><a href="{c["id"]}.html">{esc(c["title"])}</a></li>' for c in chapters)
    by_type = {}
    for n in notes:
        by_type.setdefault(n["type"], []).append(n)
    index_notes = ""
    for t, ns in sorted(by_type.items()):
        items = "".join(f'<li><a href="{esc(n["chapitre"])}.html#note-{esc(n["id"])}">{esc(n["titre"])}</a></li>' for n in ns if n.get("chapitre"))
        index_notes += f'<h3>{esc(NOTE_TYPES.get(t, t))}</h3><ul>{items}</ul>'
    src = book.get("source", {})
    src_html = f'<a href="{esc(src["url"])}">{esc(src.get("titre", src["url"]))}</a>' if src.get("url") else esc(src.get("titre", ""))
    body_html = (
        f'<h1>{esc(book["titre"])}</h1><p class="byline">{esc(book["auteur"])}</p>'
        f'<p class="presentation">{esc(book.get("description", ""))}</p>'
        f'<p class="licence">Texte : {esc(book.get("licence", "domaine public"))}. Source : {src_html}</p>'
        f'<h2>Chapitres</h2><ol class="toc">{toc}</ol>'
        + (f'<h2>Index des notes</h2><div class="notes-index">{index_notes}</div>' if notes else "")
    )
    (book_out / "index.html").write_text(page(cfg, book["titre"], body_html, 1), encoding="utf-8")

    book_json = {
        "slug": slug, "titre": book["titre"], "auteur": book["auteur"],
        "chapitres": [{"id": c["id"], "titre": c["title"], "audio": bool(base and c["meta"].get("audio", book.get("audio", False)))} for c in chapters],
        "notes": [{"id": n["id"], "titre": n["titre"], "type": n["type"], "chapitre": n.get("chapitre"), "ancrage": n.get("ancrage")} for n in notes],
    }
    (book_out / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"slug": slug, "titre": book["titre"], "auteur": book["auteur"],
            "description": book.get("description", ""), "chapitres": len(chapters), "notes": len(notes)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    root = ap.parse_args().root
    cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    out = root / "site"
    (out / "data").mkdir(parents=True, exist_ok=True)

    library = [build_book(root, cfg, out, d.name)
               for d in sorted((root / "content").iterdir())
               if (d / "book.yaml").exists() and not d.name.startswith("_")]
    (out / "data" / "library.json").write_text(json.dumps(library, ensure_ascii=False, indent=1), encoding="utf-8")

    cards = "".join(
        f'<li class="card"><a href="{b["slug"]}/index.html"><strong>{esc(b["titre"])}</strong></a>'
        f'<span>{esc(b["auteur"])}</span><p>{esc(b["description"])}</p>'
        f'<small>{b["chapitres"]} chapitres · {b["notes"]} notes</small></li>' for b in library)
    body = (f'<h1>{esc(cfg["site_title"])}</h1><p>{esc(cfg["site_description"])}</p>'
            f'<input id="filter" type="search" placeholder="Filtrer les lectures…" aria-label="Filtrer">'
            f'<ul class="cards" id="library">{cards or "<li>Aucune lecture pour le moment.</li>"}</ul>')
    (out / "index.html").write_text(page(cfg, cfg["site_title"], body, 0), encoding="utf-8")
    print(f"{len(library)} lecture(s) générée(s) dans {out}")


if __name__ == "__main__":
    main()
