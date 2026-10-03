<!-- travel-guide: {"id":"sleeper-trains","title":"Sleeper-train space and arrival planning","category":"transport","when":"Use when an overnight rail journey replaces accommodation or the next day's plan depends on sleeping aboard.","tags":["sleeper train","berth","卧铺","夜间火车"]} -->

# Sleeper-train space and arrival planning

## Activate when sleep is part of the proposition

Use this guide when an overnight train is presented as both transport and a night's accommodation. A late train with a normal hotel stay afterward does not need berth analysis. Do not treat a seat, berth, and private compartment as interchangeable products merely because all arrive at the same time.

Ask for party size, whether sharing a compartment is acceptable, upper-berth usability, luggage needs, and the minimum acceptable rest interval. Request age categories only where the selected fare or accommodation rules require them. Passenger names and identity details remain outside the planning record.

## Verify the actual sleeping product

Confirm the operator, service date, boarding and arrival stations, accommodation category, berth allocation, and whether the quoted product guarantees the required party arrangement. A search result showing several available berths does not establish that they are together or that a private compartment is included.

Verify any reservation or supplement separately from the travel ticket, plus luggage storage, access needs, and facilities that materially affect the choice. Check scheduled border or service procedures with the operator if they interrupt the proposed rest interval; do not assume uninterrupted sleep from timetable duration. For the arrival day, verify baggage storage, breakfast access if needed, and the accommodation's actual check-in arrangement.

## Choose and record

Compare the complete product and arrival-day consequences with a daytime train plus accommodation. A lower fare is not an equivalent option if it replaces the requested private space with an unconfirmed shared berth. If the required allocation cannot be established, keep it as a candidate or select a different product; do not label the space secured.

Use `planning.readiness[]` for berth arrangement and arrival-day access checks. Put the ticket and any separate required reservation in `planning.booking_tasks[]`. Represent station access and onward movements in `planning.transport_edges[]`, with the rail option using the existing intercity structure. Put local departure and arrival dates plus verified accommodation category in `event.details`; use `event.tips` for a shorter first day if rest is inadequate. Follow the [existing transport schema](../itinerary-schema.md).

## Synthetic worked scenario

Four travelers require one private compartment. A cheaper synthetic quote has four berths spread across shared compartments; another quote explicitly covers one private four-person compartment. The cheaper result does not meet the stated requirement and loses its recommendation. Arrival is 06:30, baggage storage opens at 07:30, and hotel check-in is 15:00. Replace an 08:00 timed museum booking with breakfast and a flexible local activity; the sleeper ticket alone does not establish early room access or a rested morning.
