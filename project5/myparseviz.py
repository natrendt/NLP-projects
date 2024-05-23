#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 11 09:55:55 2024

@author: jandac
"""
import spacy
from spacy import displacy
from collections import namedtuple
from termcolor import cprint


def extract_deps(deps_parse):
    """
    Extract information from dependency graph arcs.

    Parameters
    ----------
    deps_parse : spacy object
        Result of spacy.displacy.parse_deps().

    Returns
    -------
    root : int
        Index of the root of the dependency parse tree.
    deps : list of Node
        List of Nodes containg for each word:
            - position of the word (word number in text)
            - list of Edges going to the left
            - list of Edges going to the right
            - number of incoming edges
            - index of the first word accessible from this word by Edge seq
            - index of the last word accessible from this word by Edge seq.

    """
    deps = {}
    root = None
    Edge = namedtuple("Edge", ["target", "label"])
    Node = namedtuple("Node", ["word_pos", "left", "right", "links", "lspan",
                               "rspan"])
    for w in range(len(deps_parse["words"])):
        deps[w] = Node(w, [], [], 0, w, w)
    for a in deps_parse["arcs"]:
        target = a["end"]
        word_pos = a["start"]
        if a["dir"] == "left":
            target = a["start"]
            word_pos = a["end"]
        if target not in deps:
            deps[target] = Node(target, [], [], 0, target, target)
        deps[target] = deps[target]._replace(links=deps[target].links + 1)
        if a["dir"] == "left":
            deps[word_pos].left.append(Edge(target, a["label"]))
            if target < deps[word_pos].lspan:
                deps[word_pos] = deps[word_pos]._replace(lspan=target)
        else:
            deps[word_pos].right.append(Edge(target, a["label"]))
            if target > deps[word_pos].rspan:
                deps[word_pos] = deps[word_pos]._replace(rspan=target)
    for word_pos in deps:
        if deps[word_pos].links == 0:
            root = word_pos
    return root, deps


def comp_name(head_name):
    """
    Return traditional phrase name for the given head.

    Parameters
    ----------
    head_name : str
        Tag of the head word of the phrase.

    Returns
    -------
    str
        Traditional phrase name for a phrase with the given head.

    """
    phrase_name = {
        "NOUN": "NP",
        "PROPN": "NP",
        "PRON": "NP",
        "GER": "NP",
        "BREV": "NP",
        "VERB": "VP",
        "AUX": "VP",
        "FIN": "VP",
        "PRAET": "VP",
        "ADJ": "ADJP",
        "NUM": "ADJP",
        "ADV": "ADVP",
        "PART": "ADVP",
        "INTJ": "INTP",
        "DET": "DP",
        "CCONJ": "CP",
        "SCONJ": "CP",
        "ADP": "PP"
        }
    if head_name in phrase_name:
        return phrase_name[head_name]
    else:
        return ""


def print_ent(ent):
    """
    Print in color given named entitity and its label.

    Parameters
    ----------
    ent : spacy entitity
        A dict discribing a named entity.

    Returns
    -------
    None.

    """
    bkgr = {"orgName": "on_light_cyan",
            "placeName": "on_yellow",
            "geogName": "on_light_yellow",
            "persName": "on_blue",
            "date": "on_red"}
    if ent.label_ in bkgr:
        cprint(f"{ent.text} ", "black", bkgr[ent.label_], end="")
        cprint(f"{ent.label_}", "black", bkgr[ent.label_], attrs=["bold"],
               end=" ")
    else:
        cprint(f"{ent.text} ", "black", "on_light_grey", end="")
        cprint(f"{ent.label_}", "black", "on_light_grey", attrs=["bold"],
               end=" ")


def mark_components(deps_parse):
    """
    Insert brackets into a text so as to mark syntactic components.

    Parameters
    ----------
    deps_parse : spacy object
        result of spacy.displacy.parse_deps().

    Returns
    -------
    annot_sent : str
        The text with brackets with component names.

    """
    root, deps = extract_deps(deps_parse)
    word_braks = {}
    Brakets = namedtuple("Brakets", ["left", "right"])
    for w1 in range(len(deps)):
        word_braks[w1] = Brakets([], [])
    for w1 in range(len(deps)):
        x = deps[w1].lspan
        lst = word_braks[x].left
        lst.append(w1)
        word_braks[x] = word_braks[x]._replace(left=lst)
        x = deps[w1].rspan
        lst = word_braks[x].right
        lst.append(w1)
        word_braks[x]._replace(right=lst)
    annot_sent = ""
    for w1 in word_braks:
        p1 = deps_parse["words"][w1]["tag"]
        for b1 in reversed(word_braks[w1].left):
            annot_sent += f"[{comp_name(p1)} "
        annot_sent += deps_parse["words"][w1]["text"]
        for b1 in word_braks[w1].right:
            annot_sent += f" {comp_name(p1)}]"
        annot_sent += " "
    return annot_sent


def annotate_sentence_components(sent):
    """
    Insert brackets into a text to mark syntactic components.

    Parameters
    ----------
    sent : str
        Text to process (to annotate).

    Returns
    -------
    str
        Annotated text.

    """
    nlp = spacy.load("pl_core_news_sm")
    doc = nlp(sent)
    deps_parse = displacy.parse_deps(doc)
    return mark_components(deps_parse)


if __name__ == "__main__":
    line = input("Sentence: ")
    while line != "":
        print(annotate_sentence_components(line))
        line = input("Sentence: ")
