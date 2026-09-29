<!-- travel-guide: {"id":"separate-ticket-connections","title":"Separate-ticket connection decisions","category":"transport","when":"Use when consecutive journeys are sold separately or connection protection is unconfirmed.","tags":["self-transfer","separate tickets","分开出票","自行中转"]} -->

# Separate-ticket connection decisions

## Activate only for an uncertain connection contract

Use this guide when missing one leg could leave the next ticket unusable. A single search result or payment does not establish connection protection: verify the actual ticketing and carrier terms. For a confirmed protected connection, use its documented transfer requirements instead; do not impose the separate-ticket calculation automatically.

Ask for travel dates, public service identifiers, baggage handling needs, acceptable delay buffer, and whether a later arrival is tolerable. Booking references and ticket screenshots are unnecessary. The traveler can confirm document eligibility privately against the relevant official requirements.

## Build the connection backward

Verify the onward carrier's applicable check-in, bag-drop, and boarding deadlines separately. From the earliest deadline that applies, subtract the steps needed to reach that checkpoint: arrival processing, baggage collection, terminal or airport transfer, and queue allowance. Do not also count security before bag drop if it occurs afterward; check that the later boarding deadline is met too.

Use operator and airport instructions to establish which steps are required. Verify through-checking explicitly; an assumed baggage shortcut must not make the itinerary feasible. Keep estimated process times separate from published cutoffs. A published minimum connection time is not automatically a promise to protect independently purchased tickets.

## Choose and record

Accept a candidate only if the estimated chain fits and leaves the traveler-approved contingency buffer. If no supported process duration exists, leave the connection unresolved instead of manufacturing precision. Compare a later departure, an overnight stop, or a protected itinerary including the cost and consequence of a missed connection. A refundable onward ticket helps only according to its verified change deadlines and conditions.

In `planning.readiness[]`, summarize responsibility and the unresolved baggage or entry check, using the [existing readiness contract](../trip-readiness.md). Put the actual transfer path and fallback in `planning.transport_edges[]`. Use `planning.booking_tasks[]` for a decision to purchase or change the onward service after the gate passes. `event.details` should show the applicable cutoffs and assumptions; `event.tips` should state the missed-connection trigger and next verified option.

## Synthetic worked scenario

An arrival is scheduled for 12:10; onward bag drop closes at 14:00. Estimated arrival processing, bag collection, transfer, and bag-drop queue total 30 + 20 + 25 + 15 = 90 minutes. Expected completion is 13:40, leaving 20 minutes. The traveler requires 30 minutes of contingency, so this candidate fails even though the headline gap looks generous. Select a later candidate and repeat both the bag-drop and boarding checks; do not mark it feasible merely because it departs later.
