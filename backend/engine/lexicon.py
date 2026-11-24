"""Closed-class word lists and a rough word-class guesser."""
from __future__ import annotations

import re

PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "this", "that", "these", "those",
    "myself", "yourself", "himself", "herself", "itself", "ourselves", "themselves",
}
DETERMINERS = {
    "a", "an", "the", "some", "any", "all", "each", "every", "no", "neither", "either",
    "many", "much", "few", "several", "both", "another", "other", "such", "what", "which",
}
PREPOSITIONS = {
    "in", "on", "at", "by", "for", "with", "without", "through", "from", "to", "of",
    "about", "into", "onto", "over", "under", "between", "among", "during", "before",
    "after", "despite", "since", "until", "within", "across", "behind", "beyond", "like",
}
COORDINATORS = {"and", "or", "but", "yet", "so", "nor", "for"}
SUBORDINATORS = {
    "because", "since", "as", "although", "though", "while", "when", "where", "if",
    "unless", "until", "before", "after", "whether", "that", "which", "who",
}
AUXILIARIES = {"am", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "have", "has", "had"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
NEGATIONS = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "without"}
HEDGES = {"may", "might", "could", "can", "should", "often", "usually", "sometimes", "perhaps", "probably"}
CONNECTIVES = {
    "however", "therefore", "moreover", "furthermore", "additionally", "consequently",
    "nevertheless", "nonetheless", "ultimately", "instead", "meanwhile", "also", "then",
}
CLOSED = (
    PRONOUNS | DETERMINERS | PREPOSITIONS | COORDINATORS | SUBORDINATORS
    | AUXILIARIES | MODALS | NEGATIONS | HEDGES | CONNECTIVES
)
PHRASE_EQUIVALENCE: tuple[tuple[str, ...], ...] = (
    ("decide", "make a decision", "makes a decision", "made a decision", "making a decision"),
    ("decides", "make a decision", "makes a decision"),
    ("decided", "made a decision"),
    ("deciding", "making a decision"),
    ("look", "take a look", "takes a look", "took a look"),
    ("looked", "took a look"),
    ("analyze", "conduct an analysis", "conducted an analysis"),
    ("analyzed", "conducted an analysis"),
    ("support", "provide support", "provided support"),
    ("supported", "provided support"),
)
_NOUN_SUFFIXES = ("tion", "ment", "ness", "ity", "ance", "ence", "ship", "ism", "er", "or", "ist")
_ADJ_SUFFIXES = ("able", "ible", "ful", "less", "ous", "ive", "al", "ic", "ish", "ary")


def guess(word: str) -> str:
    """Return a rough word class from the lexicon and common suffixes."""
    value = re.sub(r"[^a-z]", "", (word or "").lower())
    if not value:
        return "unknown"
    if value in PRONOUNS:
        return "pronoun"
    if value in DETERMINERS:
        return "determiner"
    if value in PREPOSITIONS:
        return "preposition"
    if value in COORDINATORS:
        return "coordinator"
    if value in SUBORDINATORS:
        return "subordinator"
    if value in AUXILIARIES:
        return "auxiliary"
    if value in MODALS:
        return "modal"
    if value in NEGATIONS:
        return "negation"
    if value in HEDGES:
        return "hedge"
    if value in CONNECTIVES:
        return "connective"
    if value.endswith("ly"):
        return "adverb"
    if value.endswith("ing"):
        return "verb"
    if value.endswith("ed"):
        return "verb"
    if value.endswith(_NOUN_SUFFIXES):
        return "noun"
    if value.endswith(_ADJ_SUFFIXES):
        return "adjective"
    return "content"


def is_content(word: str) -> bool:
    """Content words are kept during validation; closed-class words may shift."""
    return guess(word) in {"content", "noun", "verb", "adjective", "adverb"}
