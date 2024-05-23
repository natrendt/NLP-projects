#!/usr/bin/python
import locale
from bs4 import BeautifulSoup
# import re
import urllib.request
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("pl_core_news_sm")
matcher = Matcher(nlp.vocab)


def process_text(text):
    doc = nlp(text)

    exercise = 4
    if exercise == 2:
        noun_pattern1 = [
            {"POS": "ADV", "OP": "?"},
            {"POS": "ADJ", "OP": "+"},
            {"ORTH": ",", "OP": "*"},
            {"POS": "ADJ", "OP": "*"},
            {"POS": "NOUN"}
        ]

        noun_pattern2 = [
            {"POS": "NOUN"},
            {"POS": "ADV", "OP": "?"},
            {"POS": "ADJ", "OP": "+"},
            {"ORTH": ",", "OP": "*"},
            {"POS": "ADJ", "OP": "*"}
        ]

        matcher.add("noun_phrase", [noun_pattern1, noun_pattern2])

    elif exercise == 3:
        preposition_pattern = [
            {"POS": "ADP", "OP": "+"},
            {"POS": "ADV", "OP": "?"},
            {"POS": "ADJ", "OP": "*"},
            {"ORTH": ",", "OP": "*"},
            {"POS": "NOUN"}
        ]
        matcher.add("preposition_phrase", [preposition_pattern])

    elif exercise == 4:
        verb_pattern1 = [
            {"POS": "VERB"},
            {"IS_SPACE": True, "OP": "*"},
            {"LOWER": "się", "OP": "*"},
            {"POS": "ADP", "OP": "?"},
            {"POS": "ADV", "OP": "?"},
            {"POS": "ADJ", "OP": "*"},
            {"ORTH": ",", "OP": "*"},
            {"POS": "ADJ", "OP": "*"},
            {"POS": "NOUN"}
        ]

        verb_pattern2 = [
            {"POS": "NOUN"},
            {"IS_SPACE": True, "OP": "*"},
            {"LOWER": "się", "OP": "*"},
            {"POS": "ADP", "OP": "?"},
            {"POS": "ADV", "OP": "?"},
            {"POS": "ADJ", "OP": "*"},
            {"ORTH": ",", "OP": "*"},
            {"POS": "ADJ", "OP": "*"},
            {"POS": "VERB"}
        ]
        matcher.add("verb_phrase", [verb_pattern1, verb_pattern2])

    matches = matcher(doc)
    spans = [doc[start:end] for _, start, end in matches]
    processed_text = text
    for span in spans:
        processed_text = processed_text.replace(span.text, f"[{span.text}]")

    print(processed_text)

def read_category(element):
    """
    Process a single category of news in the bulletin.

    Parameters
    ----------
    element : bs4 element type
        root element of the category.

    Returns
    -------
    None.

    """
    h3 = element.find("h3", class_="bulletin__category")
    try:
        category = h3.text
        print(f"Kategoria: {category}")
    except AttributeError:
        print("Nie znaleziono elementu <h3> z klasą 'bulletin__category'.")
    # options = {"compact": True}
    d1 = element.find("div", class_="bulletin__articles")
    for a1 in d1.find_all("article", class_="bulletin__article article"):
        h4 = a1.find("h4", class_="article__title")
        if h4 is not None:
            art_tit = h4.text
            print(f"------ tytuł: {art_tit}")
        d2 = a1.find("div", class_="article__content")
        without_paragraphs = True
        for t1 in d2.find_all(["p", "li"]):
            without_paragraphs = False
            process_text(t1.text.strip())
        if without_paragraphs:
            process_text(d2.text.strip())


def read_bulletin(edition):
    """
    Read one edition of the GUT bulletin.

    Parameters
    ----------
    edition : str
        Edition number or current number.

    Returns
    -------
    None.

    """
    base_url = "https://biuletyn.pg.edu.pl"
    url = f"{base_url}/{edition}"
    with urllib.request.urlopen(url) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        d1 = soup.find("div", class_="row bulletin")
        for d2 in d1.find_all("div", class_="bulletin__categories"):
            read_category(d2)


if (__name__ == "__main__"):
    import argparse
    locale.setlocale(locale.LC_ALL, "pl_PL.utf8")
    desc = "Process a GUT bulletin."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("number", type=int, nargs="?",
                        help="Bulletin number.")
    args = parser.parse_args()
    nr = "numer_aktualny"
    if "number" in args and args.number is not None:
        nr = f"biuletyn-{args.number}"
    read_bulletin(nr)
