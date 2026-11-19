# Before / after: real commits from the measurement

These are real commits from the author's repos (November 5–18, 2026),
scored by `scripts/check-commit.py`. SHAs are short hashes; the repos
are public, so the originals can be checked. Each "after" is what the
skill's rules produce — same change, same author, readable log.

## 1. The headline as a subject (R1)

**Before** — `02ab2e2`, sine-portfolio, 92 characters:

```
Add blog post: Your agent's code looks nothing like yours. Stop writing rules. Write checks.
```

Fails R1 (92 > 72). The failure mode is the most common one in the
measurement: 5 of the 13 over-long subjects are blog-post commits, and
4 of them carry the whole post headline as the subject. A subject is not a
title — it is the one line `git log --oneline` shows.

**After** — 47 characters:

```
Blog: your agent's code needs checks, not rules
```

Same meaning, fits on one line, keeps the repo's `Blog:` prefix. The
post title still exists — in the post itself, and in the PR title.

## 2. One commit that is four (R2 + R4)

**Before** — `702cb4e`, local-rag, 25 files, 13-line body:

```
Add CI pipeline, example data, and Streamlit GUI

- GitHub Actions CI: lint, unit tests, and an end-to-end smoke test
  that boots the real service with real embedding/reranker models and
  checks every example document is retrievable.
- Example documents in data/examples/ covering every supported type
  (md, txt, py, pdf, docx, html, csv, ...
```

Fails R2 (13-line body) and R4 (25 files) — and the subject itself
breaks Rule 1's one-change principle by naming three changes, even
though at 48 characters it fits the 72-character limit. The body is
doing the splitting the commits should have done — five bullets for
four concerns plus a dependency pin. Reverting the CI pipeline would
also revert the GUI — and the pin.

**After** — four commits, each one idea:

```
CI: run lint, unit tests, and a real-model smoke test
```

```
Add example documents for every supported file type
```

```
Add a Streamlit client for the API
```

```
Pin faster-whisper to av<19
```

Each subject fits, each body is at most two lines (the "why" for the
smoke test: "so the model-backed path is verified by CI, not just
locally"; for the pin: "faster-whisper 1.2.1 passes metadata_errors to
av.open, which PyAV 19 removed — with av 19, every audio/video file
fails to index"), and each commit reverts cleanly on its own.

## 3. The launch commit (R1 + R2 + R4)

**Before** — `efc3474`, local-rag, 62 files, 3,941 insertions,
91-character subject, 10-line body:

```
Local RAG: enterprise FastAPI service with ChromaDB, hybrid retrieval, and live folder sync

- MVC inside app/ (core, models, repositories, services, api/v1)
- Chunkers for text (recursive/section/fixed), code, PDF, Word, HTML,
  CSV/JSON, images (OCR), video/audio (whisper transcription)
- Retrieval: dense (ChromaDB) + BM25 (k1 1.5, b 0.75) fused with RRF k=60,
  cross-encoder rera...
```

Fails R1, R2, and R4. This is the commit a future reader most needs —
the one that creates the service — and it is the least reviewable:
62 files, a body that lists architecture the code already shows.

**After** — the service lands as a stack, bottom up:

```
Add the FastAPI service skeleton (MVC, config, health endpoint)
```

```
Add chunkers for text, code, documents, images, and audio
```

```
Add hybrid retrieval: dense + BM25 with RRF and reranking
```

```
Add live folder sync for data/documents
```

Four commits, each reviewable, each with a one-line "why" at most.
The architecture overview belongs in the README — which is where it
went.

## 4. The move that was right, and the file that should not have come along (R4 + R5)

**As-is** — `c5e8bcc`, sine-portfolio, 147 files, 204 insertions:

```
Blog: one folder per post as blog-N-MM-DD-YYYY

Each note now lives in content/blog/blog-<number>-<MM>-<DD>-<YYYY>/,
with the markdown at the folder root and images in img/. Public post
URLs (/blog/<slug>/) are unchanged.
```

The checker warns on R4, not fails: 147 files but 1.4 insertions per
file — a pure move. The subject says what it is, the body says the one
thing a reader needs (URLs unchanged). Splitting a rename across
commits would leave the tree half-moved at every step. That is the
exception working as designed — and the commit still fails overall,
because a generated build stamp (`data/generated/home-stamp.txt`) rode
along with the move and trips R5. The move was right; the stowaway
file was not. That is the R5 lesson in miniature: the file that should
not have been committed is the one nobody looks at, because the diff
is 147 files long. The layout JSONs beside it were committed with six
different November 5 commits — the repo's first day, before the
ignore rules existed — and the stamp file itself with three of them.
After that day, generated files appear twice more: this stamp, and
one training log.
