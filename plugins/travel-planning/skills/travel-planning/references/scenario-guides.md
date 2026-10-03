# Conditional planning guides

Use these references when a known trip constraint needs a more detailed decision than the standard pipeline provides. Keep route confirmation, source verification, privacy, and booking authorization in the existing workflow. A guide extends the relevant planning step; it does not make every trip collect every possible constraint.

## Find a relevant installed guide

From the plugin root, list compact discovery cards with:

```bash
python3 skills/travel-planning/scripts/list_planning_guides.py
python3 skills/travel-planning/scripts/list_planning_guides.py --query "luggage"
python3 skills/travel-planning/scripts/list_planning_guides.py --category transport
```

The command reads only the first metadata line of installed Markdown files in `references/scenarios/`. It does not read itineraries, provider configuration, browser state, or guide bodies; it does not contact services or write files. Results use paths relative to the skill folder. Query terms match the title, activation sentence, and tags, case-insensitively; all space-separated terms must match. These are discovery matches, not applicability scores or verified travel facts.

Use the returned `when` description to select references for the actual request, then read only those files. An empty result means that the installed guide collection has no match; continue with the existing planning references. A release containing no scenario guides also returns an empty list. A malformed installed header fails with a bounded diagnostic instead of silently omitting a reference. Use a stable installed directory while listing; this is not isolation from concurrent filesystem changes.

## Apply a guide without changing the itinerary contract

Collect only information that changes the specific decision. Prefer functional constraints and public operator facts over identity documents, diagnoses, booking records, or account access. Local synthetic examples illustrate reasoning and must never become factual claims about a real trip.

Keep dynamic facts tied to the actual route, service, date, and source. The guide text supplies a research method, not current availability, immigration eligibility, clinical advice, or an operator's promise. Resolve uncertainty using the existing `to_recheck` and fallback workflow. Do not invent current rules or exact buffers from a sample.

Write the result using [the existing itinerary structure](itinerary-schema.md) and [readiness fields](trip-readiness.md). Guide checklists are research working notes, not new required JSON properties, new readiness statuses, or new renderer capabilities. Preserve the original schema and user-selected scope.

## Add an independently maintained scenario

Place one Markdown reference in `references/scenarios/<id>.md`. Its first line is an HTML comment containing a JSON discovery card with exactly `id`, `title`, `category`, `when`, and `tags`. Use a lowercase hyphenated ID matching the filename; categories also use lowercase hyphenated identifiers. The remaining Markdown contains the actual decision procedure. This makes additional guides discoverable without repeatedly editing the skill entrypoint or loading every guide into context.

Keep each guide focused on a distinct decision, identify when it applies, and include a synthetic example where the procedure changes the plan. Link to existing references for shared rules. Do not add a scenario only to restate general travel advice.
