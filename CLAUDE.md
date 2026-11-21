# Lectures libres

Site statique (hébergé chez AlwaysData, sans base de données) de textes français du domaine public ou sous licence libre : texte chapitré, notes contextuelles, version audio.

## Organisation

| Dossier | Rôle | Publié ? |
|---|---|---|
| `sources/<slug>/` | Texte brut déposé par l'utilisateur + `meta.yaml` (auteur, licence, origine) | non |
| `content/<slug>/` | Contenu éditorial : `book.yaml`, `chapitres/*.md`, `notes/*.md` | non (source du build) |
| `audio/<slug>/` | MP3 par chapitre, `<id-chapitre>.mp3`, que l'utilisateur transfère sur S3 | non |
| `site/` | Site généré (`tools/build.py`). Seul `site/assets/` s'édite à la main | oui |
| `tools/` | `build.py`, scripts TTS | non |

`<slug>` = identifiant court en minuscules sans accents (`candide`). `<id-chapitre>` = `01-premier-chapitre`, préfixe numérique pour l'ordre.

## Commandes

- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Build : `.venv/bin/python tools/build.py` (n'écrit que dans `site/`)
- Déploiement : AlwaysData récupère `site/` depuis le dépôt GitHub (branche `main`). Après chaque build, committer `site/` avec le reste, puis pousser.

## Traitement d'un nouveau texte

1. Lire `sources/<slug>/` ; **vérifier la licence/domaine public** et la noter dans `book.yaml`.
2. Pour un texte Wikisource : `curl` de l'API `action=parse&page=<Titre>/Texte_entier&prop=text`, puis `python3 tools/import_wikisource.py entier.json <dossier>` (aplati les retours à la ligne, retire les numéros de page, garde les italiques). Garder les réponses brutes dans `sources/<slug>/` et les extraits Wikipédia de contexte dans `sources/<slug>/contexte/`.
3. Nettoyer (en-têtes/pieds de page Gutenberg/Wikisource, numéros de page) sans modifier le texte de l'auteur.
4. Chapitrer dans `content/<slug>/chapitres/NN-titre.md` avec front matter `titre:`. Un paragraphe = un bloc séparé par une ligne vide ; le build lui donne l'id `p1`, `p2`… Ne pas réordonner/fusionner les paragraphes après avoir créé des notes (les ancrages casseraient).
5. Créer les notes dans `content/<slug>/notes/<id>.md` (voir format ci-dessous).
6. Générer l'audio : `.venv-tts/bin/python tools/tts_generate.py <slug>` (Piper, voix `fr_FR-siwis-medium` ; modèles dans `models/`, environnement séparé `.venv-tts`, préparation du texte dans `tools/tts_text.py`). Résultat dans `audio/<slug>/`, puis mettre `audio: true` dans `book.yaml` et renseigner `audio_base_url` dans `config.yaml` quand le bucket est prêt.
7. Builder et vérifier le rendu.

## Formats

`book.yaml` : `titre`, `auteur`, `description`, `licence`, `source: {titre, url}`, `audio: true|false`.

Note :
```markdown
---
titre: Lisbonne
type: geographie   # geographie|histoire|philosophie|litterature|vocabulaire|personnage|culture
chapitre: 05-le-tremblement   # id du chapitre
ancrage: p3                   # paragraphe concerné
resume: Une ou deux phrases, lisibles seules.
sources:
  - {titre: "Wikipédia — Lisbonne", url: "https://fr.wikipedia.org/wiki/Lisbonne", licence: "CC BY-SA 4.0"}
---
Développement (« Pour aller plus loin »), quelques paragraphes en Markdown.
```
Les notes contextualisent par rapport au passage ; elles ne recopient pas la source. Si le texte d'origine a ses propres notes, les conserver (champ `origine: auteur`).

## Règles

- Notes issues de sources externes : synthèse reformulée, source citée avec sa licence ; privilégier les sources libres (Wikipédia, Wikisource, Gallica pour le domaine public). Contenu éditorial publié sous CC BY-SA 4.0 (cf. `config.yaml`).
- Pour une note qui reprend des faits peu établis, le dire ; ne pas inventer de références.
- Le site doit rester lisible sans JavaScript.
- Audio : voix Piper `fr_FR-siwis-medium` (CC BY 4.0, crédit dans le pied de page via `audio_credit`). Éviter la voix `tom` (AGPLv3). Si le texte change, régénérer les chapitres concernés (`--force`).
