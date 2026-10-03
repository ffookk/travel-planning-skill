<!-- travel-guide: {"id":"ferries-islands","title":"Ferry and island return dependencies","category":"transport","when":"Use when an island stay or excursion depends on a ferry whose return timing controls another fixed commitment.","tags":["ferry","island","轮渡","海岛返程"]} -->

# Ferry and island return dependencies

## Activate for a water-crossing constraint

Use this guide when a ferry controls access to an island, a vehicle route, or an onward booking. A sightseeing boat with no onward dependency may only need its ordinary booking check; do not turn every waterfront visit into an island evacuation plan.

Ask for travel dates, passenger count, whether a vehicle or bicycle must travel, luggage category, and the latest acceptable mainland arrival. Vehicle dimensions are relevant only when the selected service requires them; registration numbers and booking codes do not belong in shared planning notes.

## Verify the correct capacity and port

Check the operating carrier, actual departure and arrival ports, seasonal timetable, boarding cutoff, and current service notices. Separate passenger capacity from vehicle capacity. Verify the ticket product and whether a return reservation is needed; an outbound place does not prove a return place exists.

If tide, weather, or port restrictions affect this specific service, record the operator's applicable guidance and the next review point rather than inventing a generic cancellation threshold. Check access from the accommodation or final attraction to the boarding point and onward access from the arrival port. Keep disembarkation time separate from published crossing time, especially when a vehicle is involved.

## Choose and record

Work backward from the next fixed commitment using its actual arrival requirement. Include disembarkation, land transport, and a stated contingency allowance. If the final scheduled sailing is the only way to meet that commitment, make the consequence of cancellation visible. A previous-day mainland overnight can be preferable to an unsupported promise that a later boat, flight, or private charter will be available.

Use `planning.readiness[]` for return capacity and service review; use `planning.booking_tasks[]` for separate outbound and return reservations where required. Record map-supported landside port access and onward transfers in `planning.transport_edges[]`. Put the scheduled crossing in `planning.intercity_options[]` with `mode`, `from`/`to`, actual ports in `departure_station`/`arrival_station`, `service_or_train`, `door_to_door_duration`, `fare`, and `availability`; its transport event references that option's stable ID through `route_id`. For the detailed transport card, also project the selected service and ports into the same record's `route`, and the same fare display into `cost`; these are display projections, not new quotes. Keep both projections synchronized when changing the selection. Put the dated availability result, boarding location, and cutoffs in `event.details`; availability in the planning summary alone is insufficient. Use `fallback` and `event.tips` for the earlier-sailing or mainland-night trigger. Do not invent a ferry map mode or represent the crossing as a car, bus, or walk edge. Follow the [transport evidence contract](../itinerary-schema.md).

## Synthetic worked scenario

A return ferry reaches port at 16:00. Disembarkation takes an estimated 15 minutes and airport travel 75 minutes. An 18:10 flight requires arrival at the airport by 17:10 in this hypothetical scenario. The chain reaches it at 17:30, already 20 minutes late before additional contingency. Reject the same-day pairing. Select an earlier verified sailing, or move the mainland return to the preceding day and price that extra night explicitly.
