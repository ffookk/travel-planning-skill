<!-- travel-guide: {"id":"entry-transit-evidence","title":"Entry and Transit Evidence Chains","category":"readiness","when":"An international route depends on entry or transit eligibility that is not yet established for the actual connection.","tags":["entry requirements","transit evidence","入境核验","中转规则","visa","transit visa","签证","过境签"]} -->

# Entry and Transit Evidence Chains

## Activation and limits

Use this guide when a border or connection condition could invalidate the selected route. It is an evidence-gathering procedure, not immigration advice or an admissibility decision. Government authorities and carriers retain their respective decisions; a planning status cannot guarantee boarding or entry.

## Minimum functional inputs

Collect jurisdictions, airports, terminals, local travel dates, overnight connections, ticket structure, baggage-transfer arrangements, and the intended travel purpose. The traveler should answer identity-specific eligibility questions in official tools privately. Request only a necessary eligibility category or resulting logistical constraint, never passport numbers, document scans, permit numbers, full birth dates, or application records.

## Decision procedure

1. Draw the actual connection sequence, including baggage reclaim, terminal changes, airport changes, and any overnight accommodation. Establish whether the proposed process remains airside using airport and carrier evidence; do not infer this from the word “transit.”
2. Identify the responsible government's current entry and transit guidance for every relevant jurisdiction. Have the traveler check the categories applicable to their own documents and circumstances. Keep carrier boarding requirements separate from government permission.
3. For each dependency, record the question, official source, checked date, applicability conditions, and remaining uncertainty. A general page or a successful result for a different document category is not personalized evidence.
4. Compare the rule's effective date and conditions with the itinerary's local dates and actual connection. Recheck after a route, ticket, terminal, baggage, or personal-eligibility change; do not carry forward an old conclusion solely because the destination stayed the same.
5. If official sources conflict or a required condition is unclear, prepare a specific question for the traveler to resolve with the relevant authority or carrier. Keep the route conditional, or propose a different connection for user approval. Do not guess permission from a forum report or submit an application on the traveler's behalf.

## Record and fallback

Use `planning.readiness[]` for each operational dependency, with scoped `summary`, `source_ids`, `checked_at`, and official HTTPS `action_links`. `to_recheck` should identify the exact connection and unresolved condition. Use `planning.booking_tasks[]` for externally established deadlines and traveler actions; keep private eligibility evidence outside the shared workspace and HTML. Store transport facts in existing intercity or transport records. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md).

## Synthetic decision example

A fictional itinerary combines separate tickets through Airport B. The carrier confirms that baggage must be reclaimed, but the traveler's applicable permission to enter has not been established. Mark that connection unresolved and identify the government check. A different connection may be proposed, but do not relabel the original as visa-free or change the confirmed route without approval.
