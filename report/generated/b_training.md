| Measure | Value |
|---|---|
| Training time (fast, 1,186 MB of train.txt) | 0.20 h (723 s) |
| Merges learned | 49,743 |
| Peak memory | 1,668 MB |
| Machine | 11th Gen Intel(R) Core(TM) i5-1145G7 @ 2.60GHz, 8 logical CPUs, 15.7 GB RAM, Windows-11-10.0.26200-SP0, Python 3.12.10 |
| Fast vs reference, 1 MB sample | 500 merges, identical: yes; reference 369.2 s, fast 4.3 s (86x) |
| train.bin | 181,315,074 tokens (363 MB), 1.25 tokens/word, 6.54 bytes/token, encoded in 391 s |
| val.bin | 1,824,155 tokens (4 MB), 1.25 tokens/word, 6.54 bytes/token, encoded in 4 s |
| check_bins.py | passed. train: max ID 49999, 202 documents round-tripped; val: max ID 49997, 3,394 documents round-tripped |
