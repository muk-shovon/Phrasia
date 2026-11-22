"""
humanizer_layer.py
Rule-based, grammar-safe post-processing layer for AI-generated English text.
No AI model, no network, pure Python standard library.

Usage:
    from humanizer_layer import humanize_layer
    final_text = humanize_layer(api_output, strength=0.6, seed=None, formal=False)
"""
import random
import re

# ----------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------

# Overused AI phrases -> plainer alternatives ("" means drop the phrase).
_CLICHES = [
    (r"\bit is (?:important|worth) (?:to note|noting) that\b", ["note that", "keep in mind that", ""]),
    (r"\bit(?:'s| is) worth mentioning that\b", ["note that", ""]),
    (r"\bin today's (?:fast-paced|digital|modern) world\b", ["these days", "today", "right now"]),
    (r"\bin the realm of\b", ["in"]),
    (r"\bis a testament to\b", ["shows"]),
    (r"\bplays a (?:crucial|vital|pivotal|key|significant) role in\b", ["matters a lot in", "is central to"]),
    (r"\bplay a (?:crucial|vital|pivotal|key|significant) role in\b", ["matter a lot in", "are central to"]),
    (r"\bdelves into\b", ["digs into", "looks at", "explores"]),
    (r"\bdelve into\b", ["dig into", "look at", "explore"]),
    (r"\bdelving into\b", ["digging into", "looking at", "exploring"]),
    (r"\bdelved into\b", ["dug into", "looked at", "explored"]),
    (r"\bin conclusion,", ["overall,", "to wrap up,", "all in all,"]),
    (r"\bin order to\b", ["to"]),
    (r"\bdue to the fact that\b", ["because", "since"]),
    (r"\bprior to\b", ["before"]),
    (r"\bin the event that\b", ["if"]),
    (r"\bwith regard to\b", ["about", "on"]),
    (r"\ba (?:wide )?(?:range|variety|array) of\b", ["many", "all kinds of", "a mix of"]),
    (r"\ba plethora of\b", ["plenty of", "lots of"]),
    (r"\ba myriad of\b", ["many", "countless"]),
    (r"\bmyriad\b", ["countless"]),
    (r"\bnavigate the complexities of\b", ["deal with", "handle"]),
    (r"\brich tapestry of\b", ["mix of"]),
    (r"\bgame-changer\b", ["big shift", "real shift"]),
    (r"\bseamlessly\b", ["smoothly"]),
    (r"\bseamless\b", ["smooth"]),
    (r"\brobust\b", ["solid", "strong"]),
    (r"\bever-evolving\b", ["changing"]),
    (r"\bleverages\b", ["uses"]),
    (r"\bleveraged\b", ["used"]),
    (r"\bleveraging\b", ["using"]),
    (r"(?<=to )leverage\b", ["use"]),
    (r"(?<=can )leverage\b", ["use"]),
    (r"(?<=will )leverage\b", ["use"]),
    (r"\butilizes\b", ["uses"]),
    (r"\butilized\b", ["used"]),
    (r"\butilizing\b", ["using"]),
    (r"\butilize\b", ["use"]),
    (r"\butilization\b", ["use"]),
    (r"\bfacilitates\b", ["helps with"]),
    (r"\bfacilitated\b", ["helped with"]),
    (r"\bfacilitating\b", ["helping with"]),
    (r"\bfacilitate\b", ["help with"]),
]

# Inflection-safe word swaps (applied with a lower probability).
_SYNONYMS = [
    (r"\bsignificantly\b", ["greatly", "a lot", "markedly"]),
    (r"\bsignificant\b", ["major", "big", "notable"]),
    (r"\bnumerous\b", ["many", "plenty of"]),
    (r"\bvarious\b", ["different", "several"]),
    (r"\benhances\b", ["improves"]),
    (r"\benhanced\b", ["improved"]),
    (r"\benhancing\b", ["improving"]),
    (r"\benhance\b", ["improve"]),
    (r"\bdemonstrates\b", ["shows"]),
    (r"\bdemonstrating\b", ["showing"]),
    (r"\bdemonstrate\b", ["show"]),
    (r"\bensures\b", ["makes sure"]),
    (r"\bensured\b", ["made sure"]),
    (r"\bensuring\b", ["making sure"]),
    (r"\bensure\b", ["make sure"]),
    (r"\brequires\b", ["needs"]),
    (r"\brequired\b", ["needed"]),
    (r"\brequiring\b", ["needing"]),
    (r"\brequire\b", ["need"]),
    (r"\bapproximately\b", ["about", "around"]),
    (r"\bsubsequently\b", ["later", "then"]),
    (r"\bindividuals\b", ["people"]),
    (r"\bassists\b", ["helps"]),
    (r"\bassisted\b", ["helped"]),
    (r"\bassisting\b", ["helping"]),
    (r"\bassist\b", ["help"]),
    (r"\bsufficient\b", ["enough"]),
    (r"\boptimal\b", ["best"]),
    (r"\bcomprehensive\b", ["thorough", "complete", "full"]),
    (r"\bcrucial\b", ["key", "vital"]),
    (r"\bpivotal\b", ["key"]),
    (r"\ba number of\b", ["several", "a few"]),
]

_TRANSITIONS = {
    "moreover": ["Also, ", "Plus, ", ""],
    "furthermore": ["Also, ", "On top of that, ", ""],
    "additionally": ["Also, ", "On top of that, ", ""],
    "in addition": ["Also, ", "Besides, "],
    "consequently": ["So ", "As a result, "],
    "therefore": ["So ", "As a result, "],
    "thus": ["So ", ""],
    "hence": ["So ", ""],
    "however": ["But ", "Still, ", "That said, "],
    "nevertheless": ["Still, ", "Even so, "],
    "nonetheless": ["Still, ", "Even so, "],
}

# Contractions that are always safe.
_CONTRACTIONS = [
    (r"\bcannot\b", "can't"), (r"\bwill not\b", "won't"), (r"\bdo not\b", "don't"),
    (r"\bdoes not\b", "doesn't"), (r"\bdid not\b", "didn't"), (r"\bis not\b", "isn't"),
    (r"\bare not\b", "aren't"), (r"\bwas not\b", "wasn't"), (r"\bwere not\b", "weren't"),
    (r"\bhave not\b", "haven't"), (r"\bhas not\b", "hasn't"), (r"\bhad not\b", "hadn't"),
    (r"\bwould not\b", "wouldn't"), (r"\bshould not\b", "shouldn't"), (r"\bcould not\b", "couldn't"),
]
# Only contracted when another word follows (avoids "as it's." style errors).
_CONTRACTIONS_FOLLOWED = [
    (r"\bit is\b", "it's"), (r"\bthat is\b", "that's"), (r"\bthere is\b", "there's"),
    (r"\bthey are\b", "they're"), (r"\bwe are\b", "we're"), (r"\byou are\b", "you're"),
    (r"\bI am\b", "I'm"), (r"\bit will\b", "it'll"), (r"\bwe will\b", "we'll"),
    (r"\bthey will\b", "they'll"), (r"\bI will\b", "I'll"),
]

# Words that can be lower-cased safely when they stop being a sentence start.
_COMMON_STARTERS = {
    "the", "this", "it", "they", "we", "these", "there", "a", "an", "our", "their", "its",
    "as", "in", "with", "for", "when", "if", "many", "some", "most", "you", "he", "she",
    "that", "those", "what", "how", "one", "each", "both", "such", "by", "on", "at", "to", "from",
}
_SPLIT_SUBJECTS = r"(?:the|it|they|we|this|these|that|he|she|i|there|you)"

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'(\u27e6])')

_PROTECT = re.compile(
    r"```.*?```"                              # fenced code
    r"|`[^`\n]+`"                             # inline code
    r"|https?://\S+|www\.\S+"                 # urls
    r"|[\w.+-]+@[\w-]+\.[\w.-]+"              # emails
    r"|\"[^\"\n]{1,400}\""                    # "quoted text"
    r"|\u201c[^\u201d\n]{1,400}\u201d"        # curly quoted text
    r"|\b(?:e\.g|i\.e|etc|vs|Dr|Mr|Mrs|Ms|Prof|Fig|No)\.",  # abbreviations
    re.S,
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _match_case(src, rep):
    if not rep:
        return rep
    if src[:1].isupper():
        return rep[0].upper() + rep[1:]
    return rep


def _lower_first(word):
    if word and word[0].isupper() and word.lower() in _COMMON_STARTERS:
        return word[0].lower() + word[1:]
    return word


def _wc(s):
    return len(s.split())


def _apply_table(text, table, rng, prob):
    for pattern, options in table:
        def repl(m, options=options):
            if rng.random() > prob:
                return m.group(0)
            return _match_case(m.group(0), rng.choice(options))
        text = re.sub(pattern, repl, text, flags=re.I)
    return text


def _apply_transitions(text, rng, prob):
    names = "|".join(sorted(_TRANSITIONS, key=len, reverse=True))
    pat = re.compile(rf"(^|[.!?]\s+)({names}),\s+(\w+)", re.I | re.M)

    def repl(m):
        if rng.random() > prob:
            return m.group(0)
        opt = rng.choice(_TRANSITIONS[m.group(2).lower()])
        nxt = m.group(3)
        nxt = (nxt[0].upper() + nxt[1:]) if opt == "" else _lower_first(nxt)
        return m.group(1) + opt + nxt

    return pat.sub(repl, text)


def _apply_contractions(text, rng, prob):
    for pattern, rep in _CONTRACTIONS:
        text = re.sub(
            pattern,
            lambda m, rep=rep: _match_case(m.group(0), rep) if rng.random() < prob else m.group(0),
            text, flags=re.I)
    for pattern, rep in _CONTRACTIONS_FOLLOWED:
        flags = 0 if pattern == r"\bI am\b" or pattern == r"\bI will\b" else re.I
        text = re.sub(
            pattern + r"(?=\s+\w)",
            lambda m, rep=rep: _match_case(m.group(0), rep) if rng.random() < prob else m.group(0),
            text, flags=flags)
    return text


def _maybe_split(s, rng, strength):
    """Split one long sentence into two at a safe point."""
    if _wc(s) < 22 or not s.endswith(".") or rng.random() > 0.7 * strength:
        return [s]
    pat = re.compile(rf", but |; |, and (?={_SPLIT_SUBJECTS}\b)", re.I)
    cands = []
    for m in pat.finditer(s):
        if m.group(0) == "; " and s.count(";") != 1:
            continue
        left_n = _wc(s[:m.start()])
        right_n = _wc(s[m.end():])
        if left_n >= 8 and right_n >= 6:
            cands.append((abs(left_n - right_n), m))
    if not cands:
        return [s]
    m = min(cands, key=lambda c: c[0])[1]
    left = s[:m.start()].rstrip() + "."
    right = s[m.end():]
    if m.group(0).lower().startswith(", but"):
        right = "But " + right
    else:
        right = right[0].upper() + right[1:]
    return [left, right]


def _reshape_line(line, rng, strength):
    sents = _SENT_SPLIT.split(line.strip())
    parts = []
    for s in sents:
        parts.extend(_maybe_split(s, rng, strength))
    merged, i = [], 0
    while i < len(parts):
        cur = parts[i]
        if (i + 1 < len(parts) and _wc(cur) < 7 and _wc(parts[i + 1]) < 10
                and cur.endswith(".") and parts[i + 1].endswith(".")
                and rng.random() < 0.4 * strength):
            nxt = parts[i + 1]
            first, _, rest = nxt.partition(" ")
            joiner = rng.choice([", and ", "; "])
            merged.append(cur[:-1] + joiner + _lower_first(first) + (" " + rest if rest else ""))
            i += 2
        else:
            merged.append(cur)
            i += 1
    return " ".join(merged)


def _want_article(word):
    w = word.lower()
    vowel = w[0] in "aeiou"
    if w.startswith(("uni", "use", "usu", "uti", "eu", "one", "once", "ubi")):
        vowel = False
    if w.startswith(("hour", "honest", "honor", "honour", "heir")):
        vowel = True
    return "an" if vowel else "a"


def _fix_articles(text):
    def repl_lower(m):
        art, word = m.group(1), m.group(2)
        if word.isupper() and len(word) > 1:
            return m.group(0)
        want = _want_article(word)
        return m.group(0) if art == want else f"{want} {word}"

    def repl_start(m):
        pre, art, word = m.group(1), m.group(2), m.group(3)
        if word.isupper() and len(word) > 1:
            return m.group(0)
        want = _want_article(word).capitalize()
        return m.group(0) if art == want else f"{pre}{want} {word}"

    text = re.sub(r"\b(a|an)\s+([A-Za-z][A-Za-z'\-]*)", repl_lower, text)
    text = re.sub(r"(?m)(^|[.!?]\s+)(A|An)\s+([A-Za-z][A-Za-z'\-]*)", repl_start, text)
    return text


def _cleanup(text):
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r",\s*([.!?])", r"\1", text)
    text = re.sub(r"(?m)(^[ \t]*|[.!?][ \t]+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


_MD_LINE = re.compile(r"^\s*(#|[-*>|]|\d+[.)]\s)")


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def humanize_layer(text, strength=0.6, seed=None, formal=False, reduce_dashes=True):
    """
    text          : AI-generated English text (output of your humanizer API)
    strength      : 0.0 - 1.0, how aggressively to change things
    seed          : int for reproducible output, None for random
    formal        : True skips contractions (academic / business text)
    reduce_dashes : replace em dashes (an AI tell) with commas
    """
    if not text or not text.strip():
        return text
    strength = max(0.0, min(1.0, float(strength)))
    rng = random.Random(seed)

    # 1. protect code, URLs, quotes, abbreviations
    store = []

    def stash(m):
        store.append(m.group(0))
        return f"\u27e6{len(store) - 1}\u27e7"

    text = _PROTECT.sub(stash, text)

    # 2. phrase-level edits
    text = _apply_table(text, _CLICHES, rng, min(1.0, 0.9 * strength + 0.1))
    text = _apply_table(text, _SYNONYMS, rng, 0.6 * strength)
    text = _apply_transitions(text, rng, 0.8 * strength)
    if not formal:
        text = _apply_contractions(text, rng, 0.85 * strength)
    if reduce_dashes:
        text = re.sub(r"\s*\u2014\s*|\s+\u2013\s+",
                      lambda m: ", " if rng.random() < 0.7 * strength + 0.2 else m.group(0), text)

    # 3. sentence-level rhythm (skip markdown structure lines)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() and not _MD_LINE.match(line):
            lines[i] = _reshape_line(line, rng, strength)
    text = "\n".join(lines)

    # 4. cleanup, a/an fix, capitalisation
    text = _cleanup(text)
    text = _fix_articles(text)
    text = _cleanup(text)

    # 5. restore protected spans
    return re.sub(r"\u27e6(\d+)\u27e7", lambda m: store[int(m.group(1))], text)


if __name__ == "__main__":
    sample = (
        "In today's fast-paced world, it is important to note that artificial intelligence plays a crucial role "
        "in many industries. Moreover, companies utilize it to enhance productivity, and they do not always "
        "understand the risks involved in a wide range of applications. It is useful. It is also fast. "
        "However, the technology requires careful oversight \u2014 especially when it is used for an important "
        "decision. As the report says, \"AI is neither good nor bad, it depends on use.\" See https://example.com. "
        "In conclusion, we should leverage these tools responsibly and we cannot ignore the ethical questions "
        "that arise when a robust system makes a decision about a human life."
    )
    for s in (0.3, 0.6, 1.0):
        print(f"--- strength {s} ---")
        print(humanize_layer(sample, strength=s, seed=7))
        print()
