# 🧠 Cursor Agent Rules

**Project: Accuracy-First Katha Transcription (Python)**

You are a **Cursor coding agent** implementing a production-grade Python system for **Katha transcription with canonical Gurbani quote detection**.

Your top priority is **correctness and accuracy**.
Latency, elegance, and optimization are secondary.

You MUST follow all rules below.

---

## 🔑 GOLDEN RULE (NON-NEGOTIABLE)

**Do NOT proceed to the next task unless the current task:**

1. Runs without errors
2. Has tests or a runnable demo
3. Produces verifiable output
4. Includes a clear "Done Report" with evidence

If unsure → STOP. Do NOT guess.

---

## 1️⃣ HOW YOU WORK (MANDATORY)

### Rule 1: Micro-milestones only

* Break work into **small, isolated steps** (≤ 1–2 hours of coding).
* Each step must produce a **runnable artifact**:

  * CLI command, test, or demo script.
* If a task feels big, split it further.

### Rule 2: One module at a time

* Touch **max 1–3 files per milestone**.
* Do NOT jump across unrelated modules.

### Rule 3: Define inputs/outputs first

Before coding, write a short spec:

* Inputs (types, assumptions)
* Outputs (types, schema)
* Errors
* One concrete example

No spec → STOP.

### Rule 4: No feature without verification

Every milestone must include at least ONE:

* Unit test
* Integration test
* Runnable demo command

### Rule 5: Temporary shortcuts must be explicit

If something is stubbed:

* Raise `NotImplementedError` or clear placeholder
* Add `TODO(<milestone_id>)`
* List it in `KNOWN_ISSUES.md`

### Rule 6: Correctness before optimization

* Simple > clever
* Accuracy first, latency later

---

## 2️⃣ PYTHON STANDARDS (MANDATORY)

### Python version & basics

* Python **3.11+**
* No notebooks
* No hidden global state
* No hardcoded paths

### Typing & models

* All public functions **must** have type hints
* Use `@dataclass` or `pydantic` for shared models
* Do NOT pass raw dicts between modules

### Central shared schema ONLY

You must reuse shared models:

* `Segment`
* `Hypothesis`
* `QuoteMatch`
* `TranscriptResult`

No module invents its own schema.

### Module size

* Prefer files < 300 lines
* Split when necessary, not earlier

### Configuration

* No magic numbers
* All thresholds live in `config.py`
* Every config value must be documented

---

## 3️⃣ ERROR HANDLING & RELIABILITY

### Explicit exceptions only

Define custom exceptions in `errors.py`:

* `AudioDecodeError`
* `ASREngineError`
* `DatabaseNotFoundError`
* `QuoteMatchError`

Never swallow errors.

### Fail fast

* Missing DB / model → crash clearly
* Error message must explain how to fix

### Degrade safely

If uncertain:

* Keep original text
* Set `needs_review = True`
* Preserve provenance

---

## 4️⃣ LOGGING (REQUIRED)

* Use `logging.getLogger(__name__)`
* Every transcription job has a `job_id`
* Log:

  * Segment creation
  * Routing decisions
  * ASR calls + timing
  * Quote candidates count
  * Match scores + decisions
  * Review flags

Do NOT log full databases or huge payloads.

---

## 5️⃣ TESTING RULES (pytest REQUIRED)

* All tests under `tests/`
* Deterministic tests only
* No internet calls

### Required test types

* Unit tests for core logic
* Contract tests between modules
* End-to-end smoke test for pipeline

### Fixtures & snapshots

* `tests/fixtures/audio/`
* `tests/fixtures/text/`
* `tests/snapshots/*.json`

### Edge cases required

* Empty input
* Short segment
* Mixed language
* Quote-like text that should NOT match

---

## 6️⃣ PIPELINE-SPECIFIC RULES (VERY IMPORTANT)

### Canonical replacement rules

* NEVER replace text unless verified
* Require:

  * confidence ≥ threshold
  * verifier approval

Otherwise:

* Keep spoken text
* Attach candidates
* Mark review

### Provenance is mandatory

Every quote segment must store:

* `spoken_text`
* `canonical_text`
* `source metadata`
* `match_confidence`

### ASR trust rules

* Never trust one ASR output
* If low confidence or mixed language:

  * run ≥ 2 ASR engines or decodes
  * store all hypotheses

### Routing must be auditable

Store:

* `route`
* `route_reason`
* confidence rationale

### Review queue is mandatory

Uncertain == review
No exceptions.

---

## 7️⃣ STRICT BUILD ORDER (DO NOT SKIP)

1. Repo skeleton + CLI (empty JSON output)
2. VAD chunking
3. Single ASR baseline
4. Script normalization (Gurmukhi + Roman)
5. Scripture DB service (SGGS + Dasam)
6. Quote candidate detection
7. Assisted matching + canonical replacer
8. Orchestrator + ASR fusion
9. Live mode (last)

---

## 8️⃣ REQUIRED MILESTONE FORMAT

For EVERY task, output EXACTLY:

**(A) Goal**
**(B) Scope (files touched)**
**(C) Implementation steps**
**(D) Tests / commands to run**
**(E) Done report (with evidence + limitations)**

Missing section = STOP.

---

## 9️⃣ DEFINITION OF DONE (MANDATORY CHECKLIST)

Confirm ALL before proceeding:

* [ ] Type hints added
* [ ] Tests added and passing
* [ ] CLI/demo works
* [ ] Schema unchanged or updated everywhere
* [ ] Logging added
* [ ] No silent failures
* [ ] Config updated
* [ ] Known issues documented

---

## 🔧 APPROVED LIBRARIES ONLY

Do NOT invent new libraries.

* Audio: `ffmpeg`, `soundfile`, or `pydub`
* VAD: `webrtcvad` or `silero-vad`
* ASR: `openai-whisper` or `faster-whisper`
* DB: `sqlite3`
* Fuzzy matching: `rapidfuzz`
* Testing: `pytest`

---

## 🚨 FINAL RULE

If you are unsure:

* STOP
* Do NOT guess
* Ask for clarification

**Accuracy > completeness > speed**
