#!/usr/bin/python
import locale
from bs4 import BeautifulSoup
# import re
import urllib.request
import spacy
from spacy import displacy
from projekt4.myparseviz import mark_components, print_ent
from spacy.matcher import Matcher
from spacy.tokens import Span



nlp = spacy.load("pl_core_news_sm")

# zadanie 1
matcher = Matcher(nlp.vocab)

date_patterns = [
    [{'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{1,4}"}],  # DD.MM.YYYY
    [{'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{1,2}"}],  # DD.MM
    [{'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{1,4}"}, {"IS_SPACE": True, "OP": "*"}, {"LOWER": "r"}, {"ORTH": "."}],  # DD/MM/YYYY r.
]

time_patterns = [
    [{"LOWER": "godz"}, {'ORTH': '.'}, {"IS_SPACE": True, "OP": "*"}, {'IS_DIGIT': True, "OP": "{1,2}"}, {'ORTH': '.'}, {'IS_DIGIT': True, "OP": "{2}"}]  # godz. HH.MM
]

matcher.add("DATE", date_patterns)
matcher.add("TIME", time_patterns)
# koniec zadania 1

def process_text(text):
    # Print the text as is.
    print(text)
    # Print words, lemmas, POS tags, and explanations for POS tags
    doc = nlp(text)

    # zadanie 1
    matches = matcher(doc)
    spans = []
    for match_id, start, end in matches:
        span = Span(doc, start, end, label=nlp.vocab.strings[match_id])
        spans.append(span)
    filtered_spans = spacy.util.filter_spans(spans)
    with doc.retokenize() as retokenizer:
        for span in filtered_spans:
            retokenizer.merge(span)
    # koniec zadania 1

    n = 0
    for token in doc:
        n += 1
        print(f"{n:2}.", token.text, token.lemma_,
              token.tag_, spacy.explain(token.tag_))
    # Print a parse tree with components.
    deps_parse = displacy.parse_deps(doc)
    print(mark_components(deps_parse))
    n = 0
    # Print the text with named entities marked and categorized
    for ent in doc.ents:
        if ent.start_char > n:
            print(doc.text[n:ent.start_char], end=" ")
        print_ent(ent)
        n = ent.end_char
    if n < len(doc.text):
        print(doc.text[n:])
    else:
        print()



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
