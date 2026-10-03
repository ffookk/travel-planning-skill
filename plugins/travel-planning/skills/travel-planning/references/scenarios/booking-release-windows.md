<!-- travel-guide: {"id":"booking-release-windows","title":"Booking Release Windows","category":"planning","when":"Use when a selected activity or transport product is not yet on sale and its release rule determines when the traveler must act.","tags":["booking","release time","预约","放票"]} -->

# Booking Release Windows

## Activate and limit the scope

Use after route confirmation when missing a sales opening could remove a core activity. Do not use for cancellation penalties, ordinary opening hours, or products already available without a release constraint. This guide prepares a traveler action; it does not place an order, hold inventory, or create a scheduled reminder automatically.

## Minimum inputs and evidence

Collect the product and official sales channel, target visit date and session, party quantity, acceptable alternative sessions, and the operator's release wording. Obtain the rule from the operator's current booking instructions, including the publication date, applicable product, local timezone, and any holiday exception. A calendar showing unavailable dates does not establish whether sales are unopened or sold out. Community reports can suggest a release pattern but cannot confirm it.

## Decision procedure

1. Separate the target experience time from the sales opening and the latest useful decision time. A rolling number of calendar days, a monthly batch, and a release a stated number of hours beforehand require different calculations.
2. Translate the supported rule into a dated action in the operator's timezone. State that timezone explicitly; check the corresponding traveler date if they will be elsewhere. If the rule or daylight-saving interpretation is ambiguous, keep the conversion unresolved.
3. Work backward from dependent commitments. If the booking outcome arrives after a nonrefundable connection must be chosen, keep a feasible alternative route or delay that commitment.
4. Recheck the live official channel at the action time. Distinguish not released, sold out, unavailable to this party, and source failure. None means a reservation exists.

## Existing fields, gate, and fallback

Use `planning.booking_tasks[]` with `target_date`, `target_session`, `product`, `quantity`, `release_rule`, `next_action_at`, `deadline`, `priority=book_when_open`, and truthful `status`. Bind attraction tasks through `event_id`, `attraction_id`, and event `booking_task_ids[]`. Preserve evidence in `source_ids` and dated `action_links[]`; an unresolved conversion can also use `planning.readiness[]`. Follow [the existing data contract](../itinerary-schema.md).

Do not treat the event as secured until the user confirms the result. Keep `execution.fallback` executable without the scarce product.

## Synthetic decision change

A fictional museum releases visits seven calendar days beforehand at 09:00 venue time. A visit on the 18th implies action on the 11th, not seven days before the trip starts on the 16th. Because a proposed fixed excursion must be committed on the 10th, retain a different museum session or a refundable excursion instead of assuming the preferred ticket will appear.
