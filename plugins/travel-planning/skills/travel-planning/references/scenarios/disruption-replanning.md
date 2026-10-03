<!-- travel-guide: {"id":"disruption-replanning","title":"Disruption replanning around fixed commitments","category":"transport","when":"Use when a confirmed cancellation, material delay, or access closure makes part of the selected itinerary unworkable.","tags":["disruption","cancellation","交通中断","行程改排"]} -->

# Disruption replanning around fixed commitments

## Activate for a concrete broken dependency

Use this guide after a disruption affects an actual selected service or access route. A distant weather possibility belongs in ordinary contingency planning until it changes operational decisions. Confirm the affected date, service, and direction before replacing the itinerary.

Ask which commitments are fixed, the latest acceptable arrival, acceptable extra cost, and whether the traveler prefers preserving a particular activity or reducing disruption. Public service identifiers and booking conditions are sufficient; do not request account access, payment details, booking codes, or private correspondence. The traveler performs account-specific changes.

## Identify what no longer follows

Check the operator's current notice and timestamp. Separate a confirmed cancellation from an estimate or third-party alert. Trace the affected chain forward: arrival, access transfer, timed admission, luggage collection, accommodation entry, and next departure. Stop changing the plan once an unaffected anchor can still be reached with its required allowance.

Verify alternative capacity and ticket applicability independently. A service that runs is not necessarily bookable for this party, and a replacement route does not prove the original ticket is valid on it. Check change, refund, or assistance conditions with the responsible operator; do not promise an entitlement based on a generic disruption rule.

## Choose and record

Offer a small set of executable alternatives around the traveler's priorities: preserve the destination with a later arrival, preserve the timed commitment using a different route, or replace the now-unreachable activity locally. Calculate each full chain to the next fixed deadline. Keep additional expenditure separate from already-paid amounts and uncertain refunds; do not subtract an unconfirmed refund from the amount the traveler needs now.

Follow the affected event's `route_id` to its record in `planning.transport_edges[]` or `planning.intercity_options[]`. Update the selected service, dependent events, and applicable `inventory_refs[]` together. If adopting a different option, change the event's `route_id` to that option; never carry the cancelled service's quote or operational bindings onto the replacement. After rebinding dependent events, remove the cancelled option from the active transport collections. Preserve the original research result and snapshots as historical evidence outside those active collections, without rewriting their contents, and retain unaffected choices. The full page follows event references; it does not display every unused transport option. Use `planning.readiness[]` to explain the cancelled selection, notice, and any unresolved replacement capacity or ticket check. Put required user changes in `planning.booking_tasks[]` with an actionable deadline, and repeat that deadline and action in the affected transport event's visible `details` with its official `action_links[]`; an unbound task or readiness record is not displayed by the full page. The transport event's `details` should also identify the selected replacement and revised times; its `tips` should give the trigger for the next fallback. Preserve other valid event actions. Update dependent attraction admission, `preparation[]`, and execution fields when their entry, session, advance action, or fallback changes, rather than putting those instructions into hidden attraction `details` or `tips`. Use the [existing source and status contract](../itinerary-schema.md).

## Synthetic worked scenario

A 10:00 train is cancelled. The next verified candidate arrives at 13:20, followed by 30 minutes to a venue whose 13:30 session has a 13:15 entry cutoff. Arrival at 13:50 cannot work. If the operator confirms a changeable 14:30 slot with a 14:15 cutoff and capacity, select that slot and update the transfer and booking task. Otherwise choose an untimed nearby alternative; retaining the 13:30 event with a delay warning is not a repaired itinerary.
