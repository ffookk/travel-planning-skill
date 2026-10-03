<!-- travel-guide: {"id":"family-rest-rhythm","title":"Family Rest and Care Rhythm","category":"readiness","when":"A family day must fit traveler-defined rest or care windows around fixed bookings.","tags":["family pacing","rest windows","亲子节奏","休息安排"]} -->

# Family Rest and Care Rhythm

## Activation and limits

Use this guide when rest, feeding, changing, or caregiver availability affects the day's order. It does not prescribe sleep, nutrition, supervision, or medical routines. Use the family's stated needs; do not infer a universal schedule from a child's age.

## Minimum functional inputs

Collect the required care windows, their flexibility, usable rest settings, who must remain together, and how much optional activity the family wants. Ask about stroller or carrying constraints only when they change transport or access. Use anonymous party counts and only the eligibility bands needed for a published booking rule. Exact birthdays, names, and diagnoses do not belong in the planning record.

## Decision procedure

1. Place fixed commitments and traveler-defined care windows first. Distinguish a rest opportunity that can move from a commitment the family says must remain protected. Include local arrival dates and the effects of transfers on the available day.
2. Verify that each proposed care location is usable at the required time. Hotel check-in, room access, changing facilities, re-entry policies, and stroller restrictions need property or operator evidence. A nearby hotel does not imply access to a room before check-in.
3. Connect those anchors door to door, including collection of stored belongings and the actual attraction exit. Fit optional visits into the remaining time; do not fill a care window merely because admission is available.
4. Check the return path after each optional stop. If delays would consume the protected window, shorten or remove that stop before compressing the family's stated requirement.
5. Agree an order for dropping optional activities and identify a usable alternative rest location. If access to all proposed rest locations is unresolved, leave the dependent sequence unconfirmed rather than representing transit as equivalent rest.

## Record and fallback

Use normal `rest`, `meal`, `transport`, and `lodging` events in `days[].events[]`. Explain a care window's operational purpose in `details` without identifying a person. Record facility checks in `planning.readiness[]`, and required reservations or access confirmations in `planning.booking_tasks[]`. Attraction-internal pauses use `execution.checkpoints[]` with `kind=rest`. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md); preserve verified arrangements and mark unresolved access `to_recheck` with an official HTTPS action link.

## Synthetic decision example

A fictional family requests a room-based pause from 13:00 to 14:00. The property confirms room access only from 15:00. Do not place a 13:00 hotel rest event. Present either a later start with the protected pause after check-in or a separately verified alternative setting that the family accepts. Drop the optional second museum if neither fits the confirmed route.
