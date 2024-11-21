import re
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from tqdm import tqdm
import argparse
import os
import sys

ANKI_CONNECT_URL = "http://localhost:8765"

def extract_pdf_text(filepath):
    reader = PdfReader(filepath)
    pdf_text = {}
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        text = re.sub(r"\s+", " ", text)  # Clean up whitespace
        pdf_text[i] = text
    return pdf_text

def preprocess_text(text):
    # Split into sentences for embedding
    sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]

def invoke(action, **params):
    request = {"action": action, "version": 6, "params": params}
    response = requests.post(ANKI_CONNECT_URL, json=request)
    if not response.ok:
        raise Exception(response["error"])
    return response.json().get("result")

def check_relevance(note_text, pdf_embeddings, model, threshold=0.60):
    note_embedding = model.encode(note_text, convert_to_tensor=True)
    scores = util.cos_sim(note_embedding, pdf_embeddings)
    max_score = scores.max().item()
    return max_score >= threshold

def chunked_iterable(iterable, size):
    iterator = iter(iterable)
    for first in iterator:
        yield [first, *islice(iterator, size - 1)]

def find_notes_and_add_tag(pdf_filepath, tag_name, max_workers, chunk_size, similarity_threshold, anki_search_query):
    model = SentenceTransformer("all-MiniLM-L6-v2")

    pdf_text = extract_pdf_text(pdf_filepath)
    pdf_sentences = []
    for text in pdf_text.values():
        pdf_sentences.extend(preprocess_text(text))
    pdf_embeddings = model.encode(pdf_sentences, convert_to_tensor=True)

    # Step 2: Fetch Notes and Test Relevance
    notes = invoke("findNotes", query=anki_search_query)
    relevant_notes = []

    def process_notes(note_ids):
        results = []
        try:
            # Fetch notes in batch
            notes = invoke("notesInfo", notes=note_ids)
            for note in notes:
                note_id = note["noteId"]
                note_text = BeautifulSoup(note["fields"]["Text"]["value"], 'html.parser').get_text()
                if check_relevance(note_text, pdf_embeddings, model, threshold=similarity_threshold):
                    results.append(note_id)
        except Exception as e:
            print(f"Error processing notes: {e}")
        return results

    note_chunks = chunked_iterable(notes, chunk_size)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Use tqdm to show progress for parallel processing
        results = list(
            tqdm(
                executor.map(
                    lambda chunk: process_notes(chunk),
                    note_chunks,
                ),
                total=(len(notes) + chunk_size - 1) // chunk_size,
                desc="Processing notes",
            )
        )

    relevant_notes = [note_id for batch in results for note_id in batch]

    # Step 3: Tag Relevant Notes
    if relevant_notes:
        invoke("addTags", notes=relevant_notes, tags=tag_name)
    print(f"added tag \"{tag_name}\" to {len(relevant_notes)} notes")

def validate_positive_integer(value):
    """Validator to check if a value is a positive integer."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is an invalid positive integer value")
    return ivalue

def validate_threshold(value):
    """Validator to check if a value is between 0 and 1."""
    ivalue = float(value)
    if ivalue < 0.0 or ivalue > 1:
        raise argparse.ArgumentTypeError(f"{value} is an invalid threshold (must be between 0.0 and 1.0)")
    return ivalue

def validate_existing_file(path):
    """Validator to check if the provided file exists."""
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"The file {path} does not exist")
    return path

def main():
    parser = argparse.ArgumentParser(description="Find relevant Anki cards to PDF and add tag.")

    # Required positional arguments
    parser.add_argument(
        "pdf_path",
        type=validate_existing_file,
        help="Path to the PDF file to process.")
    parser.add_argument(
        "tag_name",
        type=str,
        help="tag name to apply")

    # Optional arguments with default values
    parser.add_argument(
        "--max-workers",
        type=validate_positive_integer,
        default=3,
        help="Number of parallel workers (default: 3).")
    parser.add_argument(
        "--chunk-size",
        type=validate_positive_integer,
        default=12,
        help="Number of notes to process in a chunk (default: 12).")
    parser.add_argument(
        "--similarity-threshold",
        type=validate_threshold,
        default=0.6,
        help="Similarity threshold to use (default: 0.6).")
    parser.add_argument(
        "--anki-search-query",
        type=str,
        default="\"deck:AnKing Step Deck\"",
        help="Subset of cards to search from (default: \"deck:AnKing Step Deck\").")

    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        sys.exit(1)

    find_notes_and_add_tag(
        args.pdf_path,
        args.tag_name,
        args.max_workers,
        args.chunk_size,
        args.similarity_threshold,
        args.anki_search_query)

if __name__ == "__main__":
    main()