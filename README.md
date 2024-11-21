A script that takes a path to a PDF and an Anki tag as an input, and attempts to find the relevant cards from a specified subset of cards (default is `"deck:AnKing Step Deck"`, which assumes you have the [AnKing Step deck](https://www.ankihub.net/step-deck) installed) and assign the specified tag.

# Requirements
1. must have requirements installed with `pip install -r requirements.txt`
2. must have Anki running and the [AnkiConnect add-on](https://ankiweb.net/shared/info/2055492159) installed
3. must have the [AnKing Step deck](https://www.ankihub.net/step-deck) installed, or a deck named "AnKing Step Deck" in your collection, unless you plan on modifying the subset of cards to search for using the `--anki-search-query` flag (see below)

# Usage
```bash
usage: anki_assign_tags.py [-h] [--max-workers MAX_WORKERS] [--chunk-size CHUNK_SIZE] [--similarity-threshold SIMILARITY_THRESHOLD]
                           [--anki-search-query ANKI_SEARCH_QUERY]
                           pdf_path tag_name

Find relevant Anki cards to PDF and add tag.

positional arguments:
  pdf_path              Path to the PDF file to process.
  tag_name              tag name to apply

options:
  -h, --help            show this help message and exit
  --max-workers MAX_WORKERS
                        Number of parallel workers (default: 3).
  --chunk-size CHUNK_SIZE
                        Number of notes to process in a chunk (default: 12).
  --similarity-threshold SIMILARITY_THRESHOLD
                        Similarity threshold to use (default: 0.6).
  --anki-search-query ANKI_SEARCH_QUERY
                        Subset of cards to search from (default: "deck:AnKing Step Deck").
```

## Example
```bash
python anki_assign_tags.py \
    /path/to/my/pdf.pdf \
    Foundations_of_Disease::block_3::week_7::antimicrobials \
    --max-workers 10 \
    --chunk-size 500
```