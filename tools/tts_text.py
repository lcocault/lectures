"""Prépare le texte d'un chapitre pour la synthèse vocale.

Entrée : un fichier Markdown de content/<slug>/chapitres/.
Sortie : une liste de segments (phrases ou groupes de phrases) prêts à être lus.
"""
import html
import re

from num2words import num2words

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_to_int(s):
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMAN[a]
        total += -v if ROMAN.get(b, 0) > v else v
    return total


def prepare_title(title):
    t = html.unescape(title)
    t = re.sub(r"\b([IVXL]+)\b", lambda m: num2words(roman_to_int(m.group(1)), lang="fr"), t)
    return t


def prepare_paragraph(p):
    p = re.sub(r"<abbr title=\"([^\"]*)\">.*?</abbr>", r"\1", p)
    p = re.sub(r"\b([IVXL]+)<sup>(?:e|er|re)</sup>",
               lambda m: num2words(roman_to_int(m.group(1)), to="ordinal", lang="fr"), p)
    p = re.sub(r"<[^>]+>", "", p)          # balises restantes
    p = p.replace("*", "")                # italiques
    p = p.replace(" ", " ")
    p = re.sub(r"\s*—\s*", ", ", p)       # tirets cadratins : courte pause
    p = re.sub(r"[«»]", "", p)
    p = re.sub(r"\bM\. ", "Monsieur ", p)
    p = re.sub(r"\s+", " ", p).strip()
    return p


def split_sentences(p, max_len=380):
    """Découpe en groupes d'au plus max_len caractères, aux fins de phrase si possible,
    sinon aux virgules/points-virgules, en dernier recours aux espaces."""
    pieces = []
    for sent in re.split(r"(?<=[.!?…])\s+", p):
        if len(sent) <= max_len:
            pieces.append(sent)
            continue
        for sub in re.split(r"(?<=[,;:])\s+", sent):
            while len(sub) > max_len:
                cut = sub.rfind(" ", 0, max_len)
                pieces.append(sub[:cut])
                sub = sub[cut + 1:]
            pieces.append(sub)
    chunks, cur = [], ""
    for piece in pieces:
        if cur and len(cur) + len(piece) + 1 > max_len:
            chunks.append(cur)
            cur = piece
        else:
            cur = (cur + " " + piece).strip()
    if cur:
        chunks.append(cur)
    return chunks


def chapter_segments(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    front, body = m.group(1), m.group(2)
    title = re.search(r'titre:\s*"?(.*?)"?\s*$', front, re.M).group(1)
    segs = [("titre", prepare_title(title))]
    for block in re.split(r"\n\s*\n", body.strip()):
        kind = "signature" if block.startswith('<p class="signature"') else "para"
        clean = prepare_paragraph(block)
        if clean:
            for i, c in enumerate(split_sentences(clean)):
                segs.append((kind if i == 0 else "cont", c))  # "cont" : suite d'un paragraphe
    return segs
