<!-- travel-guide: {"id":"cycling-days","title":"Cycling-day distance and fallback choices","category":"transport","when":"Use when a day's timing depends on cycling pace, route suitability, bike hire, or carrying a bicycle on another service.","tags":["cycling","bike hire","骑行","自行车路线","bike rental"]} -->

# Cycling-day distance and fallback choices

## Activate for a cycling-dependent day

Use this guide for a cycling excursion or a transport leg whose distance, surface, or bike arrangements change the schedule. A short optional ride beside an otherwise complete itinerary may only need a local activity check. Do not infer a rider's capability from age or from the group's fastest member.

Ask for a comfortable riding duration or recently familiar distance, surface preference, tolerance for climbing, bike type, and whether the group wants to stay together. A diagnosis or exercise history is unnecessary; record practical limits and offer a shorter option without making a medical judgment.

## Verify the route and equipment

Check the proposed route with official trail, park, road, or local transport sources as appropriate. Verify access conditions, closures, bike permissions, and significant surface or elevation changes. A car route or a generic map distance is not evidence of a suitable cycling route. Keep uncertain segments unresolved instead of routing riders through them by assumption.

For rental bikes, confirm pickup and return hours, size availability, permitted use, included equipment, and the process for mechanical problems. Verify bicycle acceptance and capacity on any bus, train, or ferry proposed as a fallback. A passenger timetable alone does not establish that a bike can board.

## Choose and record

Estimate riding time using the stated pace assumption, then add collection, orientation, breaks, and return. Compare the total with daylight and any rental or onward-service cutoff verified for the date. Identify a shorter route with a clear turn-back point. If a transit fallback cannot carry the bike, it is not an executable fallback unless an accepted bike-return arrangement exists.

Use `planning.readiness[]` for route access, hire fit, and fallback carriage checks. Put required bike or carriage reservations in `planning.booking_tasks[]`. For a genuine intercity ride, use `planning.intercity_options[]` with a stable `id`, `mode="cycling"`, `from`/`to`, `door_to_door_duration`, evidenced `route`, `cost`, and `fallback`. Bind a timed `transport` event to that record with `route_id`; preserve the distance, pace assumptions, return deadline, and shorter-route trigger in its `details` and `tips`. Preserve applicable route evidence and action links, and manually check that their endpoints match the structured record. This supports the transport card and binding; it does not generate or validate a cycling map.

The base mapped `transport_edges[]` and `daily_routes[]` support only car/bus/walk. A local cycling leg must remain in research or a draft until a cycling-capable route contract is available, or the traveler selects a supported transport alternative. Record this capability gap as unresolved in `planning.readiness[]`; do not finalize that cycling-dependent day. A generic `note` is not a validated replacement for its principal transport, and a local ride must not be mislabeled intercity to pass validation. Keep the day's actual geographic stops and their order accurate in research and any draft route data; never relabel a walking or driving map as cycling or claim it covers the ride. Map-supported access legs remain ordinary transport edges. Use the [existing event contract](../itinerary-schema.md).

## Synthetic worked scenario

A 30 km local loop at an assumed 10 km/h needs three hours of riding. Add 45 minutes of breaks and 30 minutes for collection and return: four hours 15 minutes. Only three hours 30 minutes are available before the confirmed return cutoff. A verified 20 km alternative totals three hours 15 minutes on the same assumptions, so it replaces the full loop in the research draft. Its small margin is explicit, not a guarantee. This timing decision does not close the base's local cycling-map capability gap: final delivery still requires a supported route contract or the traveler's chosen transport alternative.
