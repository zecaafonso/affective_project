# NovaShop Affective Assistant

Engine of an affective customer-support assistant for **NovaShop**, an online electronics store.
For every customer message the engine estimates the emotional state (valence, activity, dominance, confidence, label), keeps an emotional state over the conversation, and chooses one of six actions with a reply in English or Portuguese.

Built on the shared Affective Computing project kit. Only `engine/`, `tests/`, `evaluation/` and this README were added or changed; `harness/`, `run_app.py` and `run_scenario.py` are the original kit files.

## Group

| Topic | Expert |
| --- | --- |
| 1. Text perception | José Afonso Monteiro |
| 2. Affective model, map and optional channels | Luã Mariano |
| 3. Decision, state over time and robustness | Filipe Matos|
| 4. Software, interface, tests and demo | Daniela Rodrigues |
| 5. Evaluation, data, ethics and report | Letícia Azevedo|

## Requirements

* Python 3.9 or later. The app, the engine and the tests use the **standard library only** — nothing to install to run them.
* The evaluation script (`evaluation/`) is the only part that needs extra packages (pandas, openpyxl, scipy, scikit-learn,
  matplotlib), listed in `requirements.txt`: `pip install -r requirements.txt`. It is not needed to run the app.
* `tkinter` for the interface. On Linux, if you get `No module named tkinter`: `sudo apt install python3-tk`.
* No internet connection or online services are needed.

## How to run

Run every command from this folder (the one that contains `run_app.py`). On Linux/macOS use `python3` if `python` is not Python 3.

**Interface**

    python run_app.py

Type a message and press Enter, or pick a scenario and click **Play scenario**.
Click **Reset session** before each new scenario: the engine remembers the conversation, so without a reset the
state from the previous scenario carries over (and both end up in the same log file).

**A scenario without the interface** (prints one line per message and writes a log):

    python run_scenario.py scenarios/mandatory/M1_calm_faq.json

The four mandatory scenarios are `M1_calm_faq`, `M2_growing_frustration`, `M3_explicit_requests` and
`M4_ambiguity_and_robustness`; four practice scenarios are in `scenarios/practice/`.

**Tests**

    python -m unittest discover tests -v

## How the engine works

    text ──► engine.py ─────────────────────────────► policy.py ──────────────────► result dict
             valence, activity, confidence,            state over time, rules,
             dominance, label (topics 1 and 2)         action + reply (topic 3)

| File | Role |
| --- | --- |
| `engine/engine.py` | `Engine` class required by the contract. `process()` estimates the emotion and hands the decision to the policy; `reset()` starts a new conversation. |
| `engine/lexicon_dataset.json` | Lexicon of 747 English words, each with a valence, an activity and a label. |
| `engine/vocabulary.py` | Negations, intensifiers, dominance cue words, emotion prototypes and the neutral radius. |
| `engine/policy.py` | `ConversationManager`: emotional state over the conversation and the decision rules. Its thresholds are at the top of the file. |

### 1. Perception (`engine.py`)

* **Valence and activity:** average of the lexicon words found in the message. A negation (`not`, `never`, ...)
  flips the valence of the next known word; an intensifier (`very`, `extremely`, ...) multiplies it.
  Exclamation marks and text in capitals raise the activity.
* **Confidence:** based on how many words of the message are in the lexicon (0.25 when none are).
* **Dominance:** assertive words (`demand`, `refund`, `now`, ...), `!` and capitals raise it; hesitant words
  (`please`, `sorry`, `confused`, ...) and `?` lower it. It enables the 3D view of the map and is also passed to the policy (rules 5 and 8 below).
* **Label:** `neutral` inside a small radius around the origin; otherwise the nearest emotion prototype
  (joy, calm, anger, fear, frustration, sadness) in valence–activity–dominance space.

### 2. Decision (`policy.py`)

The policy keeps a smoothed emotional state (exponential moving average of valence, activity and dominance), counts
negative messages in a row and clarification requests in a row, and remembers whether a human was already offered. 
Rules are checked in order and the first one that matches wins:

1. Answer to a previous offer of a human: "yes" → `ESCALATE`, "no" → `ANSWER`.
2. Legal threat or formal complaint (EN/PT) → `ESCALATE`.
3. Request for a human → `OFFER_HUMAN` (or `ESCALATE` if the customer is very upset or a human was already offered).
4. Accumulated frustration (very negative and agitated state, or 3 negative messages in a row) → `ESCALATE`.
5. Dominant anger (negative message, agitated and dominant state, 2 negative messages in a row) → `ESCALATE`,
   one message earlier than rule 4.
6. A clear goodbye ("thanks", "obrigado, ficou tudo resolvido") → `CLOSE_POSITIVE`, even with low confidence.
7. Uncertain message (low confidence, very short or ambiguous) → `ASK_CLARIFICATION`, at most once in a row; then `OFFER_HUMAN`.
8. Negative message or state → `ANSWER_EMPATHIC`; after 2 negative messages in a row → `OFFER_HUMAN`.
   If the customer seems helpless (low dominance state) and no human was offered yet → `OFFER_HUMAN` at once.
9. Otherwise → `ANSWER`, with a short FAQ reply (delivery time, address change, returns, order status).

**Robustness:** sarcasm ("Great, another delay") is treated as negative with lower confidence.
Portuguese is detected and answered in Portuguese; a message in another language gets a clarification request in both languages. 
The policy never rewrites the estimated emotion. When in doubt it only lowers the confidence and chooses a safer action.

Audio and image files are accepted by `process()` but not used (no voice or face channel).

## Engine contract

`Engine.reset()` starts a new conversation. `Engine.process(text, audio_path=None, image_path=None)` returns:

| Key | Type | Meaning |
| --- | --- | --- |
| `valence` | float −1..1 | negative to positive (map x) |
| `activity` | float −1..1 | calm to agitated (map y) |
| `dominance` | float −1..1 | submissive to in control (3D view) |
| `confidence` | float 0..1 | how much the estimate can be trusted |
| `label` | str | `neutral`, `joy`, `calm`, `anger`, `fear`, `frustration` or `sadness` |
| `action` | str | `ANSWER`, `ANSWER_EMPATHIC`, `ASK_CLARIFICATION`, `OFFER_HUMAN`, `ESCALATE`, `CLOSE_POSITIVE` |
| `reply` | str | what the assistant says (English or Portuguese) |
| `flags` | list | see below |
| `details` | dict | see below; written to the session log |

**Flags:** `lang_pt`, `lang_unknown`, `sarcasm_suspected`, `ambiguous_or_short`, `low_confidence`, `human_request`, `legal_or_escalation_threat`, `accumulated_frustration`, `dominant_anger`, `helpless_user`.

**Details:**

| Key | Meaning |
| --- | --- |
| `words_count`, `matched_words` | words in the message and how many are in the lexicon |
| `negation_used` | whether a negation word appears |
| `lang` | `en`, `pt` or `unknown` |
| `sarcasm`, `valence_adjusted` | sarcasm detected, and the valence the policy used after that adjustment |
| `state_valence`, `state_activity`, `state_dominance` | emotional state over the conversation |
| `neg_streak`, `clarify_streak` | negative messages / clarification requests in a row |
| `offered_human` | whether a human was already offered in this conversation |
| `rule` | name of the decision rule that chose the action (e.g. `legal_threat`, `negative_streak_offer`) |
| `turn` | message number in the conversation |

## Tests

| File | What it checks |
| --- | --- |
| `tests/test_contract.py` | Kit test: the output respects the contract for unusual inputs, and `reset()` clears the state. |
| `tests/test_policy.py` | One test per decision rule, calling the policy directly with fixed values (independent of the lexicon). |
| `tests/test_engine.py` | Negation, intensifiers and dominance, plus the expected actions in each mandatory scenario (M1–M4). |

## Session logs

Every session writes a plain-text log to `logs/session_<date>_<time>.txt`: input, map values, confidence,
label, action, flags, latency, reply and `details` for every message. In the interface, the **Session log**
panel shows the same content and **Save log as...** copies it elsewhere. The demo video has one log per
mandatory scenario (the session was reset between scenarios):

| Scenario | Log file |
| --- | --- |
| M1 - Calm customer with simple questions | `logs/session_20261122_102524.txt` |
| M2 - Frustration that grows over the conversation | `logs/session_20261122_102639.txt` |
| M3 - Explicit requests that must not be missed | `logs/session_20261122_102747.txt` |
| M4 - Ambiguous, sarcastic and non-English messages | `logs/session_20261122_102838.txt` |

## Evaluation (SAM ratings)

Run from this folder (needs the packages in `requirements.txt`):

    pip install -r requirements.txt
    python evaluation/calcular_metricas_sam_5_avaliadores.py

| File | Role |
| --- | --- |
| `evaluation/NovaShop_SAM_5_Avaliadores.xlsx` | 28 messages from the 8 scenarios. Sheets `Avaliador_1`…`Avaliador_5`: SAM valence, arousal, dominance (1–9) and an emotion label from each rater. Sheet `Sistema`: the engine's output for each message (reset between scenarios). |
| `evaluation/calcular_metricas_sam_5_avaliadores.py` | Checks that every sheet is complete, takes the majority label (≥3 of 5 raters) and the mean SAM rating mapped to −1..1, and compares them with the engine. |
| `evaluation/Resultados_NovaShop/resumo_metricas.txt` | Accuracy, macro F1, per-class report, confusion matrix; Spearman ρ, p-value and MAE per dimension; spread between raters. |
| `evaluation/Resultados_NovaShop/resultados_avaliacao.xlsx` | Sheets `Resultados_Detalhados` (one row per message, human vs system values and errors), `Matriz_Confusao` and `Erros` (error analysis: messages where the human majority label differs from the engine's label). |
| `evaluation/Resultados_NovaShop/*.png` | Figures for the report: confusion matrix, F1 per emotion, mean human SAM vs system per dimension. |

SAM arousal is compared with the engine's `activity`. Messages from the same conversation are not independent,
so the metrics describe this small set and are exploratory.

## Known limits

* The lexicon is English only. Portuguese messages are detected and answered in Portuguese, but their emotion is mostly estimated as neutral with low confidence.
* Sarcasm detection is keyword-based and catches only simple patterns.
* Dominance comes from a short list of cue words, `!`, `?` and capitals, so it is a rough estimate; in the decision it is used only by the dominant-anger and helpless-customer rules.
* The engine cannot tell when a new scenario starts; use **Reset session** in the interface.
