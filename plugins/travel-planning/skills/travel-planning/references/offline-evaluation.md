# Offline evaluation of synthetic planning decisions

Use this optional developer tool to check a supplied answer against a small,
explicit synthetic case. It checks structured choices, pending facts and arithmetic.
It does not call a model, read a trip workspace, query providers, discover credentials,
open source URLs or write files. It does not validate a complete itinerary, prove that
a model followed a guide, or establish real availability, accessibility, legal or
medical suitability. Continue to use the existing itinerary audit for production JSON.

From the plugin directory:

```bash
python3 skills/travel-planning/scripts/evaluate_planning_case.py \
  --case synthetic-case.json --show-case
python3 skills/travel-planning/scripts/evaluate_planning_case.py \
  --case synthetic-case.json --candidate synthetic-answer.json
python3 -m unittest discover -s tests -p test_planning_evaluation.py
```

Pass only explicit files you intend to read. `--show-case` prints the prompt and
facts from that file; it excludes the evaluator's rules and example answers.
Normal evaluation prints only check IDs, outcomes and content digests. Diagnostics
do not include input values, absolute paths or exception text. There is no telemetry
or automatic output file. Shell redirection, if used, creates a file under the shell's
permissions and is outside this tool's privacy controls.

## Case and answer contracts

Every object has exactly the documented fields. Unknown fields, duplicate JSON keys,
unknown versions, invalid references, non-finite numbers, symlinks and oversized or
deeply nested input are rejected. Files are limited to 256 KiB, IDs to 80 ASCII
characters, facts to 100, rules to 40 and expression nesting to 8 levels. Numeric
values and intermediate results have an absolute bound of one trillion, at most
15 significant digits and six decimal places. JSON numeric tokens that would lose
precision on decoding are rejected, as are expressions exceeding these limits;
the checker never rounds an unsupported value into a passing answer.

A complete minimal case is:

```json
{
  "schema": "planning-case/v1",
  "id": "synthetic-route",
  "prompt": "Choose one fully evidenced accessible route: east or bus. If neither qualifies, defer with an empty route array. List unresolved access facts in pending.",
  "facts": {
    "east-access": {"description": "Synthetic east exit, selected service/date: lift availability", "value": null, "unit": "boolean", "status": "unknown"},
    "bus-access": {"description": "Synthetic bus, selected service/date: complete boarding and alighting access", "value": true, "unit": "boolean", "status": "verified"}
  },
  "rules": [
    {"id": "route", "kind": "choice", "minimum": 1, "maximum": 1, "policy": "feasible", "options": [
      {"id": "east", "requires": [{"fact": "east-access", "equals": true}]},
      {"id": "bus", "requires": [{"fact": "bus-access", "equals": true}]}
    ]},
    {"id": "pending", "kind": "pending", "facts": ["east-access", "bus-access"]}
  ],
  "examples": [
    {"id": "supported", "answers": {"route": ["bus"], "pending": ["east-access"]}, "expect": "pass"},
    {"id": "unsupported-exit", "answers": {"route": ["east"], "pending": ["east-access"]}, "expect": "fail"}
  ]
}
```

Copy the exact `case_sha256` returned by `--show-case` into an answer envelope:

```json
{
  "schema": "planning-answer/v1",
  "case_id": "synthetic-route",
  "case_sha256": "<exact digest returned by --show-case>",
  "answers": {"route": ["bus"], "pending": ["east-access"]}
}
```

The digest binds the answer to the exact case bytes, including formatting and
examples. Any case edit requires a fresh digest. This is a stale-input check, not
an authenticity signature. Answers contain every rule ID exactly once; extra or
missing IDs are invalid. Lists contain distinct IDs, never explanatory prose.

## Facts, units and executable checks

Facts have `description`, `value`, `unit` and `status`. Describe the exact service,
date, entrance, room or dietary condition that a fact supports. These descriptions
help a human author the case; the checker does not infer evidence scope from prose.
Encode each distinct required condition as its own fact and rule. `verified` is
an assertion within a synthetic fixture, never a claim of live verification.
`unknown` always has a null value. A verified false fact is a known negative, not
an unresolved fact. Supported units are `boolean`, `text`, `minutes`, `count`,
`nights`, `AUD`, `EUR` and `USD`; the last six take finite numeric values.

There are three rule kinds (with two policies for choices):

- `choice`: supply options with distinct `id` and a `requires` array. Each requirement
  is either `{"fact":"id","equals":true}` (boolean or text equality), or
  `{"left":EXPRESSION,"op":"le","right":EXPRESSION}`. Numeric operators are
  `le`, `ge` and `eq`, with identical units on both sides. Every requirement must be
  verified and satisfied. `minimum` and `maximum` bound the selected array. If fewer
  than `minimum` options qualify, the only passing answer is an empty array, meaning
  **defer the requested choice**. A lone qualifying restaurant therefore cannot
  complete a two-option normal-meal requirement. If enough options qualify, an
  empty answer fails. `policy: "feasible"` accepts any qualifying selection within
  the count bounds. It does not rank preferences.
- `choice` with `policy: "cheapest"`: set both counts to 1 and add `cost: EXPRESSION`
  to every option. Costs must use one currency and be nonnegative. Select any tied
  cheapest eligible option. If any eligible option's cost is unknown, defer with
  an empty array; the tool cannot prove the comparison. Optional activities should
  be absent from a committed-cost expression. Currency conversion is unsupported.
- `quantity`: supply `expression`; answer with `{"value":NUMBER,"unit":"minutes"}`
  or another matching numeric unit. Arithmetic is exact within the bounded decimal
  domain above, with no rounding tolerance. If any operand is unknown, the answer must preserve the
  unit with a null value. For clock calculations, authors must convert all input
  instants to minutes on **one declared date/time-zone axis**. The evaluator does
  not parse local clock strings, resolve daylight-saving ambiguity or infer dates.
- `pending`: supply distinct `facts` IDs. The answer must contain exactly the unknown
  facts from this list. Use it alongside choices to require unresolved constraints
  to remain visible. It does not schedule a real-world verification task.

Expressions are a closed grammar: `{"fact":"id"}`, `{"op":"sum","args":[...]}`,
`{"op":"min","args":[...]}`, `{"op":"max","args":[...]}` or
`{"op":"scale","factor":-1,"arg":...}`. Numeric arguments must share units;
the dimensionless factor has an absolute bound of 1,000. For example, departure
minus walking and contingency is a sum with two negative scales. Fare capping is
`min(sum(applicable fares), applicable cap)`. Expressions cannot read files,
execute code, reference environment variables or load modules.

## Results and reusable case additions

Exit 0 means all declared checks passed; exit 1 means a well-formed answer failed
at least one check; exit 2 means `invalid_arguments`, `invalid_case` or `invalid_candidate`. A passing
report's scope is `synthetic_decision_fields`. Unsupported checks are invalid rather
than silently skipped. A valid deferral may pass, but is not a ready-to-travel plan.

Optional bundled families live in `references/evaluation-cases/<family>/*.json`.
The shared test discovers them without changing a central registry. Each installed
case must include both passing and failing examples. Add independently useful
perturbations: change a critical fact to reverse the decision, preserve irrelevant
facts to test stability, and include plausible wrong answers such as ignoring
retrieval time or treating an unknown lift as available. The shared tests evaluate
the answers, not the wording of scenario guides.

Example answers are regression fixtures, not evidence of model quality. For a blind
exercise, show only `--show-case` output to the candidate author and retain the raw
answer before inspecting the oracle. Case authors still need independent review:
a mistaken fact, requirement or unit can make the checker reward the wrong decision.
