<!-- travel-guide: {"id":"cycling-days","title":"Cycling-day distance and fallback choices","category":"transport","when":"Use when a day's timing depends on cycling pace, route suitability, bike hire, or carrying a bicycle on another service.","tags":["cycling","bike hire","骑行","自行车路线"]} -->

# Cycling-day distance and fallback choices

## Activate for a cycling-dependent day

Use this guide for a cycling excursion or a transport leg whose distance, surface, or bike arrangements change the schedule. A short optional ride beside an otherwise complete itinerary may only need a local activity check. Do not infer a rider's capability from age or from the group's fastest member.

Ask for a comfortable riding duration or recently familiar distance, surface preference, tolerance for climbing, bike type, and whether the group wants to stay together. A diagnosis or exercise history is unnecessary; record practical limits and offer a shorter option without making a medical judgment.

## Verify the route and equipment

Check the proposed route with official trail, park, road, or local transport sources as appropriate. Verify access conditions, closures, bike permissions, and significant surface or elevation changes. A car route or a generic map distance is not evidence of a suitable cycling route. Keep uncertain segments unresolved instead of routing riders through them by assumption.

For rental bikes, confirm pickup and return hours, size availability, permitted use, included equipment, and the process for mechanical problems. Verify bicycle acceptance and capacity on any bus, train, or ferry proposed as a fallback. A passenger timetable alone does not establish that a bike can board.

## Choose and record

Estimate riding time using the stated pace assumption, then add collection, orientation, breaks, and return. Compare the total with daylight and any rental or onward-service cutoff verified for the date. Identify a shorter route with a clear turn-back point. If a transit fallback cannot carry the bike, it is not an executable fallback unless an accepted bike-return arrangement exists.

Use `planning.readiness[]` for route access, hire fit, and fallback carriage checks. Put required bike or carriage reservations in `planning.booking_tasks[]`. Describe the cycling leg, estimated duration, and shorter alternative in `planning.transport_edges[]`; do not claim the existing car/bus/walk map modes prove a cycling route. `event.details` should show distance, pace assumptions, and the return deadline; `event.tips` should specify when to take the shorter route. Use the [existing event contract](../itinerary-schema.md).

## Synthetic worked scenario

A 30 km route at an assumed 10 km/h needs three hours of riding. Add 45 minutes of breaks and 30 minutes for collection and return: four hours 15 minutes. Only three hours 30 minutes are available before the confirmed return cutoff. A verified 20 km alternative totals three hours 15 minutes on the same assumptions, so it replaces the full loop. Its small remaining margin is explicit; it is not a guarantee against delays.
