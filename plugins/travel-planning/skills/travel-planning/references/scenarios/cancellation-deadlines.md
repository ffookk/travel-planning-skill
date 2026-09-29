<!-- travel-guide: {"id":"cancellation-deadlines","title":"Cancellation Deadlines and Exposure","category":"planning","when":"Use when a provisional booking or proposed purchase has a cancellation deadline that affects the order of itinerary commitments.","tags":["cancellation","refund exposure","取消期限","退改"]} -->

# Cancellation Deadlines and Exposure

## Activate and limit the scope

Use when keeping or changing a reservation may create a charge, lose a deposit, or make another commitment impractical. This is a planning comparison, not a legal interpretation or an instruction to cancel. Do not use it to calculate sales release times or to promise a refund from a generic platform label.

## Minimum inputs and evidence

Identify the exact product, applicable stay or travel dates, party scope, amount already committed, remaining payment, and the deadline wording with timezone. Ask for only the relevant terms if the user supplies a booking; omit names, confirmation numbers, payment details, and account links from research and HTML. For an unpurchased option, use the current operator or seller terms for that exact offer. Record whether the evidence describes cancellation, modification, no-show, partial cancellation, or a credit instead of cash.

## Decision procedure

1. Build a small decision table of the next relevant deadlines and the amount exposed after each one, preserving original currencies. Separate refundable charges, retained deposits, excluded fees, and amounts whose treatment is unknown.
2. Convert relative wording into an explicit local date and time only when the contract supports the interpretation. Resolve whether “before arrival” means a clock time, calendar day, or elapsed hours. Do not assume a grace period or statutory entitlement.
3. Order itinerary decisions around those boundaries. Prefer resolving a dependent ticket or route before a flexible hotel becomes inflexible. Avoid retaining two conflicting bookings past their safe decision points.
4. At the decision point, recheck the terms applicable to the exact offer or existing booking, including any confirmed changes, and the user's actual booking status. Do not substitute today's generic public policy for an existing booking's terms. A prepared alternative does not authorize cancellation or replacement.

## Existing fields, gate, and fallback

Store a concise action and exposure summary in `planning.readiness[]`, with `deadline`, `status`, `checked_at`, `source_ids`, and `action_links[]`. Use an existing `booking_tasks[]` item where a purchase decision already exists; keep the task `action` explicit. Put the execution consequence in the affected event's `details` or `execution.fallback`. Do not add reservation identifiers. See [readiness handling](../trip-readiness.md).

If a key term remains unclear, mark it `to_recheck` and retain a viable plan that does not depend on receiving a refund.

## Synthetic decision change

A fictional hotel permits cancellation until 18:00 on the 12th; a needed tour is confirmed only on the 13th. The traveler should decide by the 12th whether to keep the hotel independently of the tour or choose a different flexible stay. Waiting for the tour while describing the hotel as “free cancellation” would hide the approaching exposure.
