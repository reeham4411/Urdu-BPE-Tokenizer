| Tokenizer | Vocabulary | Tokens | Tokens per word | Bytes per token |
|---|---:|---:|---:|---:|
| Ours (Urdu BPE 50k) | 50,000 | 1,864,014 | 1.25 | 6.56 |
| GPT-2 (gpt2) | 50,257 | 8,763,431 | 5.86 | 1.39 |
| GPT-4o (o200k_base) | 200,019 | 2,445,261 | 1.64 | 5.00 |

test.txt: 3,394 documents, 1,495,267 words, 12.22 MB.

On test.txt our tokenizer needs 1.25 tokens per word, against 5.86 for GPT-2 (4.7 times as many), which falls back to raw bytes for most Urdu letters. o200k_base needs 1.64 (1.31 times ours): a 50k vocabulary spent on one language beats a 200k vocabulary shared by many. Among the hand-picked inputs, o200k_base does better on Urdu with English and Roman Urdu: text that our Urdu-only corpus rarely contains. It also does better on numbers and dates, because our pattern gives every digit its own token (section 2).
