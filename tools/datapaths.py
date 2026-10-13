"""Where the cleaned corpus and the tokenizer work files live.

The split files are not in Git, so every tool and test asks this module for
their location instead of hard-coding a path. The lookup order is:

    1. the environment variable URDU_CLEAN_DIR (folder with train.txt etc.)
    2. <repo>/data/clean, the folder clean_corpus.py writes to

Files that the tokenizer work derives from the corpus (the 1 MB sample, audit
reports, train.bin and val.bin) go to a separate work folder, so that the
cleaned corpus itself is never written to:

    1. the environment variable URDU_WORK_DIR
    2. a folder named bpe_work next to the clean folder

Example (PowerShell):
    $env:URDU_CLEAN_DIR = "E:/LLM A1/Urdu tokenizer data-.../Urdu tokenizer data/clean"
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
END_OF_TEXT = "<|endoftext|>"


def clean_dir():
    env = os.environ.get("URDU_CLEAN_DIR")
    return Path(env) if env else ROOT / "data" / "clean"


def work_dir(create=False):
    env = os.environ.get("URDU_WORK_DIR")
    path = Path(env) if env else clean_dir().parent / "bpe_work"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def split_path(split):
    """Path of train.txt, val.txt or test.txt."""
    return clean_dir() / f"{split}.txt"


def sample_path():
    """The 1 MB sample of train.txt used to compare the two trainers."""
    return work_dir() / "sample_1mb.txt"
