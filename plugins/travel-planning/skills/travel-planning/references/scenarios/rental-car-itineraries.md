<!-- travel-guide: {"id":"rental-car-itineraries","title":"Rental-car days and return constraints","category":"transport","when":"Use when a rental vehicle changes access to stops or its collection and return conditions constrain the itinerary.","tags":["rental car","return cutoff","租车","异地还车"]} -->

# Rental-car days and return constraints

## Activate for a rental-dependent route

Use this guide when stops depend on a rented vehicle or the rental period competes with another transport option. It is not needed for a simple taxi transfer or a driver-operated service; those have different operating and responsibility arrangements.

Request the intended driving days, driver count, luggage and seating needs, transmission preference, and willingness to drive after a long arrival. Ask for a licence jurisdiction or age band only when needed to check the selected rental terms. The traveler should verify eligibility privately without copying licence numbers, payment details, or identity documents into planning files.

## Verify the vehicle and the boundary days

Check the rental provider's rules for the selected pickup and return branches, hours, late arrival, after-hours return, allowed route, additional drivers, mileage, fuel or charge condition, and one-way return. Confirm required equipment and any route-dependent restrictions with the appropriate official sources. Do not assume one branch's services apply to another.

Verify that the vehicle category fits the party and bags; a seat count alone does not establish luggage capacity. For the final day, include refueling or charging, unloading, inspection or key return, and travel from the branch to the next departure point. For the first day, include collection and orientation instead of starting the drive at the flight's arrival time.

## Choose and record

Compare only the days that benefit from a car. A central-city day can change the result once parking, collection detours, and an extra rental day are included. Keep verified charges, estimated operating costs, and refundable deposits distinct; a deposit is not automatically a consumed trip expense. If an essential return process remains unconfirmed, use an earlier staffed return or another transport arrangement.

Record eligibility and return-process checks in `planning.readiness[]`. When authoring `state/itinerary-plan.json`, append tasks for the vehicle and necessary equipment to the plan-level `booking_tasks[]`; the assembler combines them with generated attraction tasks in the output `planning.booking_tasks[]`. Do not put the custom list under the plan's `planning.booking_tasks`, which replaces that combined list. Represent pickup, driving, and branch-to-station movements in `planning.transport_edges[]`. Put the branch address, return condition, and latest departure from the last stop in `event.details`; place the missed-return alternative in `event.tips`. Use the [existing transport and cost contract](../itinerary-schema.md).

## Synthetic worked scenario

The draft reaches the rental branch at 17:00. The selected branch's synthetic confirmed hours end at 16:00, and after-hours return is unconfirmed. A final viewpoint visit adds 90 minutes. Removing it produces a 15:30 return and preserves a 30-minute allowance before closure. Keep the shorter day, or price a confirmed later return arrangement; do not retain the viewpoint by assuming a key box exists.
