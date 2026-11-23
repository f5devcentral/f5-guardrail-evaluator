# Synthetic dataset library, version 1

108 paired scenarios: 12 each for prompt injection, jailbreaking, sensitive data leakage, PII exposure, harmful content, unauthorised agent actions, benign interactions, safe refusals, and ambiguous/edge cases. Seven additional guided customer demonstrations cover protection, output recovery, escape, benign interaction, independent testing, benign input/unsafe response, and a safe refusal.

All names, records and budgets are invented. Email addresses use reserved `example.invalid`; no genuine credentials, live exfiltration URLs, real customer records or actionable tools are included. Harmful-response fixtures are deliberately concise and non-operational; unauthorised actions are text claims, never executed actions.

Labels are authored for a policy forbidding unauthorised disclosure, threats/harassment, instruction-hierarchy bypass, and unauthorised tool actions. Input and response labels are independent. Metadata documents a rationale for each. Security education, quoted suspicious text, chess terminology and authorised defensive work are benign under this policy. Safe-refusal inputs are unsafe and their response fixtures safe. Different customer policies may disagree; review and relabel before treating results as deployment evidence.

This is a demonstration/smoke-test library, not a statistically representative or independently validated efficacy benchmark. Some response wording repeats across cases. Class balance and template overlap limit generalisation. Fixed `demo_input`/`demo_output` metadata supplies intentionally varied teaching outcomes; it is ignored by the live client and never inferred from ground truth. CSV examples omit mock outcome metadata; therefore all their offline demo outcomes default to cleared. Use paired JSONL or guided demos for prepared storylines.

`python scripts/build_samples.py` reproduces the files and packaged UI copies. The actual uploaded bytes are SHA-256 hashed for each run. Do not commit customer datasets to this repository.
