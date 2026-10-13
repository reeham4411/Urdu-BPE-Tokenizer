| Number rule | test.txt tokens | Tokens on numbers |
|---|---:|---:|
| one digit per piece (final) | 1,864,014 | 106,164 |
| one to three digits (variant) | 1,814,905 | 54,761 |

Splitting every digit costs 2.71% more tokens on test.txt (49,109 tokens; numbers take 1.94 times as many tokens) and frees 1,822 vocabulary slots that the variant spends on multi-digit numbers.
