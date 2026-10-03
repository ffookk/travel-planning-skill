<!-- travel-guide: {"id":"itinerary-change-impact","title":"Itinerary Change Impact Review","category":"planning","when":"Use when an accepted itinerary changes in date, party size, location, transport, or a fixed appointment and dependent research must be reconsidered.","tags":["change impact","replanning","行程变更","依赖复核","hotel","flight","酒店变更","航班变更"]} -->

# Itinerary Change Impact Review

## Activate and limit the scope

Use after a concrete change to an accepted plan, including a changed flight, hotel location, party size, visit date, or timed activity. Do not rerun destination discovery for a cosmetic title edit. The objective is to identify what the change invalidates while retaining evidence that remains applicable; this is not permission to modify reservations.

## Minimum inputs and evidence

Record the old and new planning facts, the affected stable entity and event IDs, and which commitments are already fixed. Use only the status and terms needed for planning, without collecting order identifiers or passenger records. Obtain a new date or operating change from the relevant official operator or the user's explicit instruction, distinguishing a confirmed change from a proposal.

## Decision procedure

1. Identify direct dependencies: an event's `route_id`, `attraction_id`, `lodging_id`, `meal_id`, `weather_id`, and `booking_task_ids`. Then follow the next practical effects, such as an altered arrival changing a meal anchor or a new hotel changing the first and last transport edges.
2. Classify evidence for reuse. A location identity may remain valid; dated admission, inventory, weather, meal snapshots, prices, and departure constraints may require replacement. Unchanged query inputs do not excuse an already expired snapshot.
3. Recompute only affected decisions: door-to-door intervals, meal feasibility, room-nights, required quantities, and deadline exposure. Keep the original feasible branch until the replacement has its essential facts resolved. A route-level change may require renewed user confirmation under the existing route gate.
4. Before replacing submitted research, choose a supported workspace lifecycle. If `brief.json`, `selected-route.json`, or another assignment revision input changes, initialize a fresh workspace with a distinct trip ID, record the revised brief and confirmed route there, and create new assignments. The existing CLI does not overwrite assignment IDs or submitted result/source files; do not patch persisted revisions or delete the old evidence to force a merge. Reuse still-applicable facts only by submitting them through the new assignments with their original source evidence and verification dates, after rechecking applicability; do not copy old submitted results as current. Then merge the new workspace, resolve conflicts, and reassemble. Updating a hash alone is not an impact review. Re-run the existing audit and inspect the affected daily route and event cards.

## Existing fields, gate, and fallback

Use existing research result `event_bindings[]`, `constraints[]`, `unresolved[]`, and `source_ids[]` to communicate the impact. In the active revised workspace, update `state/itinerary-plan.json`, its selected collection IDs and decisions, and `research_state_sha256` after reviewing the merged state. Preserve the prior workspace as the previous plan; even with unchanged brief inputs, an existing submitted task cannot be overwritten in place. Use a fresh workspace for its replacement until a supported replacement lifecycle exists. Rebind selected offers through `inventory_refs[]`, and update `planning.daily_routes[].stops[]` when locations change. Keep short user actions in `planning.readiness[]`. Follow [the planning pipeline](../planning-pipeline.md) and [workspace rules](../research-workspace.md).

If a critical replacement cannot be verified, retain a feasible alternative and label the unresolved decision. Do not carry an old confirmed status onto new query conditions.

## Synthetic decision change

A fictional hotel moves from the city center to the airport while the museum date stays fixed. Museum identity evidence can remain, but the morning transport edge, evening return, meal anchors, and daily route map must change. If the new morning journey misses timed admission, choose a later session or reject the hotel change rather than merely editing the lodging name.
