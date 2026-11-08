# PromoFinder — Kuku AI Generalist Assignment (Problem 1)

An offline, reproducible screenplay-to-promo ranking prototype. **All 50 screenplay episodes are used for inference, not training**. Scores are editorial heuristics, not estimated watch-through or CTR. Screenplay text is proprietary; **do not upload this data to a public GitHub repository or public Streamlit deployment.** Use a private evaluation environment or run locally, and share raw outputs only via the authorized submission channel.

## Setup / Run (Python 3.10+)

No pip installs are required for the command-line engine:

```bash
python -m src.promofinder --input data --output outputs --top 20
python -m unittest discover -s tests -v
```

`data/` must contain `episode-001-....txt` etc. To run a new show, replace `--input` with a directory of `episode-*.txt` scripts following the same timestamped format. The tool does not require video footage or paid APIs.

Optional local reviewer UI:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
- `src/promofinder.py`: robust event-level parser, candidate generation, heuristic scores, diversity re-ranker, JSON/CSV outputs
- `tests/test_promofinder.py`: timestamp, parsing, full-pack run/format tests
- `outputs/promos_ranked.json`: generated ranked recommendations, segment timestamps, quoted hook/cliff evidence, scores
- `outputs/promos_ranked.csv`: spreadsheet-friendly export
- `outputs/quality_audit.json`: dataset integrity/coverage/limitations
- `outputs/best_per_episode.json`: 50 candidates, one for every supplied episode
- `report_overleaf.tex`: the requested two-page Overleaf document source

## Pipeline design
1. Parse timestamped action, dialogue, camera events; ignore camera events during semantic ranking to prevent duplicate visual descriptions from swamping dialog.
2. Enumerate event-boundary-aligned continuous spans 25–55 sec (a conservative subset of the permitted 20–60 sec).
3. Score first ~3 sec for immediate conflict; last ~7 sec for unresolved statements or questions; score introductory entity/reference density for standalone clarity; include tension and speech density.
4. Deduplicate heavily overlapping clips within each episode, then select a diverse show-wide top 20 with at most one clip per episode.
5. Export exact episode/start/end and evidence trace for editorial review.

## Method and limitations
**Scoring weights:** hook 29%, cliffhanger 30%, standalone proxy 21%, tension 10%, dialogue density 6%, duration desirability 4%, with penalties for weak hook/cliff. Scores are **not calibrated probabilities**.

No annotated positive/negative promo examples were supplied, so there is **no supervised model training or held-out classification accuracy**. No temporal video validation. String matching may overvalue dramatic words and question marks, confuse resolved questions with cliffhangers, or incorrectly penalize clips that make sense visually. Transitions crossing scene cuts within the same episode may be jarring. The reviewer should reject low-context hooks and false cliffhangers. Only continuous, single-episode clips are produced; montage selection is not implemented.

## Human quality review template
For each of top 10, watch original footage and label (0/1 each): immediate hook ≤3 sec, standalone clarity, unresolved cliffhanger, timestamp continuity, 20–60 sec, posting-ready. Record failure reason. Report `passing / reviewed`, not classification precision unless independently labeled ground truth exists. Run a blind comparison against human-chosen or random eligible windows before claiming uplift.

## Adaptation to stronger models
`evaluate()` is the exchange point: preserve event parsing, timestamp constraints, deterministic post-filtering and JSON output; substitute an API-based local/window scoring model only with rights-approved inputs. Add LLM judges for causal clarity and unresolved tension, with cached responses, structured JSON validation, and human review; estimate costs from candidate/window count before deployment.

## Responsible data handling
The source scripts belong to Kuku and the assignment explicitly says not to publish/share the input pack. The distributable code archive deliberately excludes `data/`. Extract the supplied confidential Kuku ZIP into `data/` for local use. Never commit the input pack. Do not put the raw dialogue outputs in a public repo unless Kuku authorizes distribution.
