<!-- travel-guide: {"id":"travel-pass-value","title":"Travel-pass value for the selected itinerary","category":"transport","when":"Use when deciding between a transport pass and individual tickets for an already selected set of journeys.","tags":["travel pass","fare comparison","交通通票","周游券"]} -->

# Travel-pass value for the selected itinerary

## Activate after the journeys are chosen

Use this guide when a pass could replace fares on the confirmed route. Do not build extra journeys merely to make a pass look economical. If the route is still undecided, compare explicit candidate itineraries separately instead of presenting one blended savings figure.

Ask for intended dates, public origin/destination pairs, required service classes, party count, and only the eligibility categories relevant to the product. The traveler can check age or residency evidence privately. Names, document scans, card numbers, and pass activation codes are unnecessary for this decision.

## Verify comparable coverage

From the issuing operator's terms, check covered operators, routes, zones, dates, exclusions, reservation requirements, supplements, and activation rules. Resolve whether the validity described for this product follows calendar days, elapsed time, selected travel days, or another explicit rule; do not assume that a product called a day pass lasts 24 hours.

Use fares for the services the traveler would actually choose, including realistic available advance fares where applicable. A flexible full fare is not a fair comparator if the traveler would otherwise buy a cheaper restricted ticket and accepts its conditions. Conversely, do not compare a flexible pass against unavailable promotional fares. Keep prices in the same verified currency and preserve each quote's conditions.

## Choose and record

Compare total payable amounts for the same journeys: pass price plus uncovered legs and required supplements versus individual tickets plus their required charges. Show flexibility or convenience separately from cash savings. For uncertain optional trips, report the additional eligible fare needed to reach break-even; do not count them as committed savings.

Use `planning.readiness[]` for coverage and eligibility checks, and `planning.booking_tasks[]` for pass purchase, activation review, or required reservations. Record the chosen fare basis on affected `planning.transport_edges[]` without describing included rides as universally free. In `event.details`, identify pass coverage and any separate reservation; use `event.tips` for the first excluded leg or activation deadline. If the pass is budgeted, count its purchase once through the [existing cost model](../itinerary-schema.md), avoiding duplicate pass and individual-fare baselines.

## Synthetic worked scenario

A hypothetical pass costs 60 currency units. The selected eligible journeys cost 18 + 16 + 20 = 54 individually. Required reservations cost eight under either option. The pass totals 68 versus 62 for tickets, so tickets win by six. If a separately desired, now-confirmed journey adds 14 eligible units without a new supplement, tickets become 76 while the pass stays 68. Only that actual itinerary change reverses the recommendation.
