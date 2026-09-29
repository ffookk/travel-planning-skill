<!-- travel-guide: {"id":"ev-road-trips","title":"EV charging stops that support the route","category":"transport","when":"Use when an electric vehicle route depends on charging away from a confirmed overnight charger.","tags":["EV","charging","电动车","充电路线"]} -->

# EV charging stops that support the route

## Activate for a charging dependency

Use this guide when a road trip's distance or sequence requires public charging, or when the first or last rental day depends on a particular charge level. A short local drive already covered by a confirmed usable charge does not need a full charging itinerary.

Request the vehicle model or rental category, usable battery information when available, expected starting charge, luggage load category, and the traveler's preferred reserve. Do not request account credentials, payment tokens, location history, or a vehicle identifier. Unknown starting charge stays an assumption to check at collection.

## Verify the charging chain

Confirm connector compatibility, access hours, vehicle access restrictions, payment options, and the selected site's operational information with the charging operator. Verify rental charging and return conditions with the provider. A map pin is a candidate, not evidence that a compatible charger is usable on arrival.

Estimate energy for each leg with a stated consumption assumption and explain relevant uncertainty such as route elevation or weather. Do not convert a charger label's maximum power directly into a promised stop duration: the vehicle, starting charge, charging curve, sharing, and queues can change it. Distinguish driving time, charging time, and any queue allowance.

## Choose and record

Apply the chosen reserve to each leg, including a reachable alternative charger. Two chargers behind the same closed access gate do not provide independent fallback access. If the fallback cannot be reached within the reserve assumption, shorten the leg or charge earlier. Where charging time remains uncertain, avoid placing a non-changeable timed visit immediately afterward.

In `planning.readiness[]`, record compatibility, payment readiness, and return-charge checks using the [existing evidence contract](../trip-readiness.md). Use `planning.transport_edges[]` for legs with explicitly estimated door-to-door duration and charging fallback. Put a reservation in `planning.booking_tasks[]` only if the operator actually supports and requires one. `event.details` should carry starting-charge and consumption assumptions plus the planned charging interval; `event.tips` should identify the trigger for taking the earlier charger. Do not label these calculations as a vehicle guarantee.

## Synthetic worked scenario

A hypothetical vehicle has 50 kWh usable capacity. Starting at 80% with a 20% reserve leaves 30 kWh for the next leg. At an assumed 18 kWh per 100 km, a 220 km gap needs 39.6 kWh and fails the plan. A compatible charging stop after 120 km changes the route from infeasible to a candidate. It becomes the selected route only after access, onward energy, and an independently reachable fallback are checked.
