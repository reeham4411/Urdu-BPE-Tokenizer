r"""Byte-level BPE tokenizer for Urdu, written from scratch (CS 417, Assignment 1).

Specification (from the handout)
--------------------------------
* Base vocabulary: the 256 byte values, IDs 0 to 255. ID i is bytes([i]).
  An Urdu letter is two UTF-8 bytes, so a four-letter word starts as 8 IDs.
* Special token: "<|endoftext|>" has ID 256. It is never split, and it never
  takes part in a merge: training cuts the text at it before counting pairs,
  and encode() emits 256 for every occurrence.
* Merges: IDs 257 to 49,999, in the order learned. 50,000 - 257 = 49,743
  merges. Merge number k (1-based) creates ID 256 + k.
* Pre-tokenisation: a regular expression splits text into words before pairs
  are counted, so a merge never crosses a word boundary. A leading space
  belongs to the word after it (" word"), as in GPT-2. The pattern must keep
  Urdu words whole: combining marks (category M, e.g. zer U+0650, pesh
  U+064F, superscript alef U+0670) and ZWNJ (U+200C, category Cf) occur
  inside words in this corpus.
* Tie-breaking: when two pairs have the same count, merge the GREATER pair,
  comparing the pairs as tuples of bytes, (vocab[a], vocab[b]). Compare the
  byte strings, not the IDs: ID 257 can stand for b"ab", which is smaller
  than b"b" (ID 98) as bytes although 257 > 98.
* Lossless: decode(encode(text)) == text for every Unicode string, including
  emoji, English, newlines and "". normalize() is NOT called here; the corpus
  was normalised once by clean_corpus.py.

Conventions the tests rely on
-----------------------------
* tok.merges is a list of (a, b) ID pairs in the order learned; merges[i]
  created ID 257 + i.
* tok.vocab is a dict ID -> bytes with vocab[i] == bytes([i]) for i < 256,
  vocab[256] == b"<|endoftext|>" and vocab[257 + i] == vocab[a] + vocab[b]
  for merges[i] == (a, b).
* Pairs inside a word are counted at every position, overlapping ones
  included: the word "aaa" holds the pair (a, a) twice. Applying a merge
  replaces occurrences left to right without overlap: "aaa" -> [aa, a].
* If no pair is left before vocab_size is reached (a tiny corpus), training
  stops early and len(tok.merges) is smaller than requested.
* train_reference and train_fast produce identical merges on the same input
  (tests/test_fast_matches_reference.py).

Allowed: the standard library, regex, numpy, tqdm. No tokenizer libraries.
"""
import heapq
import json
import time
from collections import Counter, defaultdict

import regex  # third-party module: supports \p{L}, \p{M}, \p{N}

SPECIAL_TOKEN = "<|endoftext|>"
SPECIAL_ID = 256
N_BYTES = 256
FIRST_MERGE_ID = 257
VOCAB_SIZE = 50_000
N_MERGES = VOCAB_SIZE - FIRST_MERGE_ID  # 49,743

# Pre-tokenisation pattern, one alternative per kind of piece:
#   1. a word: letters, combining marks and ZWNJ, with one optional leading space
#   2. a single digit, with one optional leading space, so every number is
#      cut the same way (1947 -> 1 9 4 7, never 194 7)
#   3. punctuation and symbols: anything that is not space, letter, mark,
#      digit or ZWNJ, with one optional leading space
#   4. whitespace not followed by a non-space (so the last space of a run is
#      left to join the next word), then any remaining whitespace
# Every character falls in exactly one class, so "".join(pieces) == text.
PATTERN = (r" ?[\p{L}\p{M}\u200c]+"
           r"| ?\p{N}"
           r"| ?[^\s\p{L}\p{M}\p{N}\u200c]+"
           r"|\s+(?!\S)"
           r"|\s+")


def _merge(ids, pair, new_id):
    """Replace every occurrence of pair in ids, left to right without overlap."""
    a, b = pair
    out = []
    i, n = 0, len(ids)
    while i < n:
        if i < n - 1 and ids[i] == a and ids[i + 1] == b:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out


def _inverted(b):
    """A key that sorts byte strings in reverse order, for a min-heap:
    each byte x becomes 255 - x and a final 256 makes a prefix sort after
    the longer strings that start with it."""
    return tuple(255 - x for x in b) + (256,)


class BPETokenizer:
    """Byte-level BPE with one special token. See the module docstring."""

    def __init__(self, pattern=PATTERN):
        """Create a tokenizer with only the 256 byte tokens and <|endoftext|>.

        Attributes (names are used by the tests and the Part C scripts):
            self.pattern  the pre-tokenisation pattern string
            self.merges   list[tuple[int, int]], empty
            self.vocab    dict[int, bytes] with IDs 0..256
            self.ranks    dict[tuple[int, int], int], pair -> new ID, for encode
            (plus your compiled regex and the per-word encode cache)
        """
        self.pattern = pattern if pattern is not None else PATTERN
        self._regex = regex.compile(self.pattern)
        self.merges = []
        self.vocab = {i: bytes([i]) for i in range(N_BYTES)}
        self.vocab[SPECIAL_ID] = SPECIAL_TOKEN.encode("utf-8")
        self.ranks = {}
        self._cache = {}

    def _add_merge(self, pair):
        new_id = FIRST_MERGE_ID + len(self.merges)
        self.merges.append(pair)
        self.vocab[new_id] = self.vocab[pair[0]] + self.vocab[pair[1]]
        self.ranks[pair] = new_id
        return new_id

    def _reset(self):
        self.merges = []
        self.vocab = {i: self.vocab[i] for i in range(FIRST_MERGE_ID)}
        self.ranks = {}
        self._cache = {}

    # ------------------------------------------------------------------
    # Pre-tokenisation
    # ------------------------------------------------------------------
    def pretokenize(self, text):
        """Split text (which contains no special token) into words.

        Returns list[str] with "".join(result) == text.
        Targets: "اُردُو زبان" -> ["اُردُو", " زبان"]; a word with a ZWNJ
        inside, such as the one for "international", stays one piece.
        """
        return self._regex.findall(text)

    def split_special(self, text):
        """Cut text at every "<|endoftext|>" and return the ordinary pieces
        between the markers (possibly empty strings). Training uses it so that
        pairs never cross a marker; encode needs a variant that also tells
        where the markers were. (encode uses the same list: a marker sits
        between every two consecutive pieces.)
        """
        return text.split(SPECIAL_TOKEN)

    def _iter_words(self, text):
        """Pre-tokens of text (a str or an iterable of str), never crossing a
        marker."""
        docs = [text] if isinstance(text, str) else text
        for doc in docs:
            for piece in self.split_special(doc):
                yield from self._regex.findall(piece)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train_reference(self, text, vocab_size=VOCAB_SIZE, verbose=False):
        """Straightforward BPE, kept to check train_fast against.

        text: one str (may contain "<|endoftext|>").
        Learns vocab_size - 257 merges into self.merges, self.vocab and
        self.ranks (fewer if the corpus runs out of pairs).

        In words:
          1. cut at the special token, pre-tokenise each piece, and turn every
             word occurrence into its own list of byte IDs;
          2. repeat: count every adjacent pair in every list, take the pair
             with the highest count (ties to the greater (bytes, bytes)), give
             it the next ID, and rewrite every list.
        Recounting everything after each merge is slow on purpose: it is
        simple enough to trust.
        """
        self._reset()
        words = [list(w.encode("utf-8")) for w in self._iter_words(text)]
        n_merges = vocab_size - FIRST_MERGE_ID
        started = time.perf_counter()
        while len(self.merges) < n_merges:
            counts = Counter()
            for w in words:
                counts.update(zip(w, w[1:]))
            if not counts:
                break
            v = self.vocab
            # highest count; ties to the greater (bytes, bytes); two different
            # ID pairs can spell the same bytes, so the IDs decide last
            pair = max(counts, key=lambda p: (counts[p], v[p[0]], v[p[1]], p))
            new_id = self._add_merge(pair)
            words = [_merge(w, pair, new_id) if len(w) > 1 else w for w in words]
            if verbose and len(self.merges) % 100 == 0:
                print(f"merge {len(self.merges)}: {v[new_id]!r} count {counts[pair]} "
                      f"{time.perf_counter() - started:.0f} s", flush=True)

    def train_fast(self, text, vocab_size=VOCAB_SIZE, verbose=False):
        """The same algorithm as train_reference, fast enough for train.txt.

        text: a str, or an iterable of str (for example documents read one at
        a time from train.txt, so the 743 MB file is never one Python string).
        Must learn exactly the same merges as train_reference.

        Two of the handout's optimisations apply to training:
          1. each distinct word is counted once and its pairs are weighted by
             the word's frequency;
          2. after a merge, counts are updated only for the words that
             contained the merged pair, using an index pair -> words.
        (The third one, the per-word cache, belongs to encode.)
        verbose: print progress (merge number, pair, count, elapsed time).

        Best pair: a heap of (-count, inv(bytes a), inv(bytes b), -a, -b, a, b)
        where inv reverses byte order (see _inverted), so the smallest entry
        is the highest count, then the greatest byte pair, then the greatest
        IDs, the same order as train_reference. Entries are never removed
        when a count changes; a new entry is pushed instead, and a popped
        entry whose count no longer matches is skipped (lazy deletion).
        """
        self._reset()
        started = time.perf_counter()
        word_freq = Counter(self._iter_words(text))
        words = [list(w.encode("utf-8")) for w in word_freq]
        freqs = list(word_freq.values())
        del word_freq
        if verbose:
            print(f"{len(words):,} distinct words, {sum(freqs):,} occurrences, "
                  f"{time.perf_counter() - started:.0f} s", flush=True)

        counts = defaultdict(int)
        index = defaultdict(set)  # pair -> indices of the words that contain it
        for i, w in enumerate(words):
            f = freqs[i]
            for p in zip(w, w[1:]):
                counts[p] += f
                index[p].add(i)

        inv = {i: _inverted(b) for i, b in self.vocab.items()}

        def entry(p):
            a, b = p
            return (-counts[p], inv[a], inv[b], -a, -b, a, b)

        heap = [entry(p) for p in counts]
        heapq.heapify(heap)

        n_merges = vocab_size - FIRST_MERGE_ID
        while len(self.merges) < n_merges and heap:
            item = heapq.heappop(heap)
            pair = (item[-2], item[-1])
            if counts.get(pair, 0) != -item[0]:
                continue  # stale entry
            count = -item[0]
            new_id = self._add_merge(pair)
            inv[new_id] = _inverted(self.vocab[new_id])

            delta = defaultdict(int)
            for i in index.pop(pair):
                old = words[i]
                new = _merge(old, pair, new_id)
                f = freqs[i]
                for p in zip(old, old[1:]):
                    delta[p] -= f
                for p in zip(new, new[1:]):
                    delta[p] += f
                old_pairs, new_pairs = set(zip(old, old[1:])), set(zip(new, new[1:]))
                for p in old_pairs - new_pairs:
                    if p != pair:
                        index[p].discard(i)
                for p in new_pairs - old_pairs:
                    index[p].add(i)
                words[i] = new

            for p, d in delta.items():
                if not d:
                    continue
                counts[p] += d
                if counts[p] > 0:
                    heapq.heappush(heap, entry(p))
                else:
                    del counts[p]
                    index.pop(p, None)

            if verbose and (len(self.merges) % 1000 == 0 or len(self.merges) <= 10):
                print(f"merge {len(self.merges):,}: {self.vocab[new_id]!r} count {count:,} "
                      f"heap {len(heap):,} {time.perf_counter() - started:.0f} s", flush=True)

    # ------------------------------------------------------------------
    # Encoding and decoding
    # ------------------------------------------------------------------
    def encode(self, text):
        """Return the list of token IDs for text.

        Every "<|endoftext|>" becomes ID 256 and is never split. Every other
        piece is pre-tokenised; each word becomes its bytes, merged by applying
        the learned merges in the order they were learned (lowest new ID
        first), with the per-word cache in front. encode("") == [].
        """
        out = []
        for k, piece in enumerate(self.split_special(text)):
            if k:
                out.append(SPECIAL_ID)
            for word in self._regex.findall(piece):
                out.extend(self._encode_word(word))
        return out

    def _encode_word(self, word):
        ids = self._cache.get(word)
        if ids is None:
            ranks = self.ranks
            ids = list(word.encode("utf-8"))
            while len(ids) > 1:
                pair = min(zip(ids, ids[1:]), key=lambda p: ranks.get(p, VOCAB_SIZE * 2))
                if pair not in ranks:
                    break
                ids = _merge(ids, pair, ranks[pair])
            ids = tuple(ids)
            self._cache[word] = ids
        return ids

    def decode(self, ids):
        """Return the text for a list of IDs (the inverse of encode).

        Join the bytes of all IDs first and decode once: one token may hold
        half of a UTF-8 character. An ID list that is not valid UTF-8 (only
        possible when built by hand) must not crash.
        """
        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path):
        """Write the tokenizer to path: the pattern, the special token and its
        ID, and all merges in order (49,743 for the final tokenizer). The file
        must be enough to rebuild vocab and ranks. Prefer a text format a
        reader can inspect.

        Format: JSON with the pattern, the special token and its ID, and the
        merges as [a, b] ID pairs, one per line, in the order learned.
        """
        head = json.dumps({"type": "byte-level BPE", "pattern": self.pattern,
                           "special_token": SPECIAL_TOKEN, "special_id": SPECIAL_ID,
                           "first_merge_id": FIRST_MERGE_ID, "n_merges": len(self.merges)},
                          ensure_ascii=False, indent=1)
        merges = ",\n".join(f"  [{a}, {b}]" for a, b in self.merges)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(head[:-2] + ',\n "merges": [\n' + merges + "\n ]\n}\n")

    @classmethod
    def load(cls, path):
        """Rebuild a tokenizer from a file written by save()."""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if data["special_token"] != SPECIAL_TOKEN or data["special_id"] != SPECIAL_ID:
            raise ValueError(f"{path}: unexpected special token")
        tok = cls(data["pattern"])
        for a, b in data["merges"]:
            tok._add_merge((a, b))
        return tok
