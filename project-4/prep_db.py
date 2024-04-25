#!/usr/bin/python
import regex
from gensim.corpora import Dictionary
from gensim.corpora.mmcorpus import MmCorpus
from gensim.models import OkapiBM25Model
from gensim.similarities import SparseMatrixSimilarity
import json
import pdfplumber
from getlawacts import get_law_acts
from datetime import date
# import termcolor


def dehaphenize(s):
    """
    Joins word parts that were cleft by hyphenation.
    Note that it does not work across pages.
    It would be easy to use (\n|\f), but pages may have headers and footers,
    as well as footnotes.

    Parameters
    ----------
    s : str
        String to dehyphenize.

    Returns
    -------
    str
        Dehyphenized string.

    """
    return regex.sub(r"(\p{L}+)-\n(\p{L}+)", r"\1\2", s)


class ReadPdfFiles:
    def __init__(self, file_list, ddir, verbose):
        self.file_list = file_list
        self.ddir = ddir
        self.verbose = verbose
        self.act_no = 1

    def __iter__(self):
        for entry in self.file_list:
            if self.verbose:
                print(f"{self.act_no}. from {entry[0]}: {entry[1]}")
                self.act_no += 1
            with pdfplumber.open(f"{self.ddir}/{entry[0]}") as pdf:
                tokenized_corpus = []
                for p in pdf.pages:
                    t = dehaphenize(p.extract_text())
                    ptt = [r for r in regex.findall(r"\b\p{L}+\d*\b", t)]
                    tokenized_corpus.extend(ptt)
            yield tokenized_corpus


def prep_db(start_date, number, delay, ascending, verbose=False,
            ddir="./Data"):
    """
    Prepare database of law acts.

    Parameters
    ----------
    start_date : Date
        Which publication date to start with.
    number : int
        How many law acts to download and process.
    delay : int
        How many seconds to wait between downloading acts.
    ascending : bool
        Whether to download acts published on the date and after (True)
        or before (False).
    verbose : bool, optional
        Whether to print what the program is doing. The default is False.
    ddir : str, optional
        Where to store the data. The default is "./Data".

    Returns
    -------
    None.

    """
    import os.path
    fname = f"{ddir}/downloaded_acts.json"
    if not os.path.isfile(fname):
        file_list = get_law_acts(start_date.year, start_date.month,
                                 start_date.day, number, delay, ascending,
                                 ddir, verbose)
    else:
        file_list = json.load(open(fname))
    if verbose:
        print("Creating a dictionary")
    dictionary = Dictionary(ReadPdfFiles(file_list, ddir, verbose))
    dictionary.save(f"{ddir}/dictionary.pkl")
    bm25_model = OkapiBM25Model(dictionary=dictionary)
    bm25_model.save(f"{ddir}/bm25_model.pkl")
    if verbose:
        print("Creating a bm25 corpus")
    bow_corpus = [dictionary.doc2bow(text) for text
                  in ReadPdfFiles(file_list, ddir, verbose)]
    bm25_corpus = bm25_model[bow_corpus]
    # bm25_corpus.save(f"{ddir}/bm25_corpus.pkl")
    MmCorpus.serialize(f"{ddir}/bm25_corpus.mm", bm25_corpus)
    bm25_index = SparseMatrixSimilarity(bm25_corpus, num_docs=number,
                                        num_terms=len(dictionary),
                                        normalize_queries=False,
                                        normalize_documents=False)
    bm25_index.save(f"{ddir}/bm25_index.pkl")
    if verbose:
        print("Database created.")


if (__name__ == "__main__"):
    import argparse
    today = date.today()
    default_end_date = f"{today.day:02}.{today.month:02}.{today.year:04}"
    parser = argparse.ArgumentParser(description="Get legal acts.")
    parser.add_argument("-s", "--start_date", type=str,
                        help="Starting date dd.mm.yyyy")
    parser.add_argument("-e", "--end_date", type=str,
                        help="Ending date dd.mm.yyyy",
                        default=default_end_date)
    parser.add_argument("-n", "--number",
                        default=100, type=int,
                        help="Number of acts to download")
    parser.add_argument("-d", "--delay",
                        default=3, type=int)
    parser.add_argument("-f", "--folder", type=str, default="Data",
                        help="Folder for storing data")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print what the programs is doing.")
    args = parser.parse_args()
    if "start_date" in args and args.start_date is not None:
        the_date = args.start_date
        asc = True
    else:
        the_date = args.end_date
        asc = False
    datelst = the_date.split(".")
    if len(datelst[0]) == 1:
        datelst[0] = '0' + datelst[0]
    mydate = date.fromisoformat(f"{datelst[2]}-{datelst[1]}-{datelst[0]}")
    prep_db(mydate, args.number, args.delay, asc, args.verbose, args.folder)
