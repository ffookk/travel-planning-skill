# Audited final delivery

Use `render_itinerary.py` for previews and drafts. Use `finalize_itinerary.py` for a final artifact: it requires an explicit `workflow.phase="final"`, runs the existing audit under final rules on the exact loaded itinerary, and only then renders that same object. A failed audit, invalid input, or rendering failure does not overwrite existing delivery files. The command does not promote a draft or repair source evidence automatically.

```sh
python3 skills/travel-planning/scripts/finalize_itinerary.py \
  itinerary.json itinerary.html --report itinerary.final-audit.json
```

Standalone JSON needs no research workspace. Its receipt explicitly reports `conflicts_not_checked`; this must not be presented as a review of a research workspace. The final audit includes the existing selected-inventory freshness and final-verification checks. It checks the supplied evidence, without querying providers or proving that availability, prices, or opening conditions remain true after publication. Run `audit_itinerary.py` locally for detailed blocking messages and warnings; the final-delivery command prints only a generic refusal or binding hash.

When an offline-capable renderer is installed, add `--private-offline` (or call `finalize(..., private_offline=True)`) to audit and export through its private offline profile. A renderer without that explicit API is rejected before publication; the command never falls back to a regular online-capable export. The default remains the regular profile. The receipt records which profile was requested. An offline export retains the itinerary's private details and is not anonymized or automatically safe to share.

## Research provenance

The assembler adds `research_context` with schema `itinerary-research-context/v1` and the expected `research_state_sha256`. It contains no local paths. An itinerary carrying this provenance requires `--workspace`, and the finalizer checks the current `state/research.json` against that digest. Re-merge and reassemble when research changes. Older research-based itineraries without this field should also supply the workspace explicitly; the finalizer cannot discover omitted provenance in arbitrary JSON.

```sh
python3 skills/travel-planning/scripts/finalize_itinerary.py \
  .travel-research/trip/artifacts/itinerary.json \
  .travel-research/trip/artifacts/itinerary.html \
  --workspace .travel-research/trip
```

`--research-sha256` optionally asserts an additional expected digest. The default receipt path is `OUTPUT.final-audit.json`. Input, HTML, receipt, research state, and decision files must have distinct output/input destinations. The research state must resolve inside the supplied workspace.

## Conflicting facts used by the itinerary

`latest_submission_wins` is a merge choice, not a final evidence decision. The finalizer follows explicit IDs from day events, daily routes, and readiness items into planning objects, including their referenced candidates and supporting objects. Conflicts on those used entities require a decision. Known planning candidates with no reachable reference do not block delivery. When a research entity uses a different ID or has no mappable reference, its usage must be declared explicitly; an unknown conflict is never silently treated as unused.

Supply `--conflict-decisions decisions.json` only when decisions or usage mappings are needed. The document binds to the exact bytes of the itinerary and research state. Its `conflict_sha256` is SHA256 of the entire conflict record serialized as UTF-8 JSON with sorted keys, compact separators, `ensure_ascii=False`, and `allow_nan=False` (the script's `canonical()` helper). Do not hash a paraphrase or just the selected value.

```json
{
  "schema_version": "itinerary-conflict-decisions/v1",
  "itinerary_sha256": "<SHA256 of itinerary.json bytes>",
  "research_sha256": "<SHA256 of state/research.json bytes>",
  "entity_usage": [],
  "decisions": [
    {
      "conflict_sha256": "<SHA256 of canonical conflict record>",
      "selected_value": "Official entrance",
      "itinerary_pointer": "/planning/attractions/0/entrance/name",
      "reason": "The applicable official notice confirms this entrance.",
      "source_ids": ["official-entrance-notice"]
    }
  ]
}
```

A decision must select a value recorded for that entity and field, cite a source ID registered in the itinerary, give a reason, and point to the matching value inside the used itinerary entity. When a field has a history such as A → B → C, every current conflict record still needs its own hash-bound decision, but all decisions select the same final value and pointer; C is valid for both records. A new value absent from the entire field history should first be merged into research. During workspace conflict checks, referenced duplicate planning IDs are rejected rather than guessing which representation the renderer uses; an object's identical `id` and `entity_id` aliases are allowed. This extra ownership check does not run in standalone `conflicts_not_checked` mode. The finalizer validates these bindings; the caller remains responsible for evaluating the cited source's authority and applicability. It does not rewrite the itinerary, research, or the conflict record.

The decision pointer must match the conflict's dot-separated field path, not an unrelated field containing the same text. Two narrow representation mappings are supported: `canonical_name` maps to `name` when the itinerary entity has that field, and `facts.<path>` maps to the same `<path>` directly on the itinerary entity when present (otherwise the original nested path is used). Other renamed or transformed fields are rejected; this version does not infer their semantic equivalence or accept arbitrary field aliases.

If a shared entity has a different ID, add an `entity_usage` entry such as `{"entity_id":"shared-attraction","usage":"used","itinerary_pointer":"/planning/attractions/0","reason":"This is the selected attraction."}`. The pointer must identify a reachable itinerary object. A genuinely unselected, otherwise unmappable candidate can instead use `{"entity_id":"unused-shared-candidate","usage":"unused","reason":"This candidate was excluded from the chosen route."}`. A directly referenced entity cannot be declared unused. These declarations are caller attestations, not automatic proof of semantic equivalence.

## Receipt and publication limits

The successful receipt records exact input, HTML, optional research, and optional decision SHA256 values, plus a deterministic `binding_sha256` over those four hashes and the `export_profile` (`regular` or `private-offline`). It also records audit time, warning/event counts, and conflict decision counts. It excludes input payloads, absolute paths, source links, and raw audit messages. Hashes detect mismatched artifacts; they are not digital signatures or a certification of travel safety. Keep the receipt with the HTML and original input.

Both files are fully staged before publication and each replacement is atomic. Ordinary replacement failures restore previous files; a crash or power loss between two file replacements is not a filesystem transaction, so compare the recorded HTML hash before using a recovered pair. An exceptional rollback failure is reported explicitly and preserves remaining original backups in mode-0600 `.final-delivery-*` files beside the targets for local recovery, without logging their contents or paths.
