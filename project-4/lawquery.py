#!/usr/bin/python
import json
from gensim.corpora import Dictionary
# from gensim.corpora.mmcorpus import MmCorpus
# from gensim.test.utils import datapath
from gensim.models import TfidfModel, OkapiBM25Model


def handle_gensim_query(query, ddir, threshold, N):
    """
    Prints N most relevant document in the corpus for the query
    using gensim if their similarity is above the specified threshold.
    :param query: the query
    :return: nothing.
    """
    print("Results:")
    global N, Threshold
    acts = json.load(open(f"{ddir}/downloaded_acts.json"))
    dictionary = Dictionary.load(f"{ddir}/dictionary.pkl")
    bm25_index = OkapiBM25Model.load(f"{ddir}/bm25_index.pkl")
    tfidf_model = TfidfModel(dictionary=dictionary, smartirs='bnn')
    tfidf_query = tfidf_model[dictionary.doc2bow(query)]
    similarities = bm25_index[tfidf_query]
    i = 1
    for (s, n) in sorted(zip(similarities, acts),
                         key=lambda x: x[0], reverse=True):
        i += 1
        if i > N or s < threshold:
            break
        print("{0}: {1}".format(s, n))


if (__name__ == "__main__"):
    import argparse
    desc = "Handle queries about acts of law."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-f", "--folder", type=str, default="Data",
                        help="Location of the database.")
    parser.add_argument("-t", "--threshold", type=float, default=0.1,
                        help="Return docs with similarity above threshold.")
    parser.add_argument("-n", "--number", type=int, default=10,
                        help="Return up to that many documents.")
    args = parser.parse_args()
    line = input("Query: ")
    while line != "":
        query = line.split(" ")
        handle_gensim_query(query, args.folder, args.threshold, args.number)
        line = input("Query: ")
