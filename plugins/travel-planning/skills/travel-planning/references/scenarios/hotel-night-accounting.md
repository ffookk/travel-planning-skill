<!-- travel-guide: {"id":"hotel-night-accounting","title":"Hotel Night and Room Accounting","category":"planning","when":"Use when arrival times, consecutive stays, multiple rooms, or early access make the required hotel nights or quoted room-nights unclear.","tags":["hotel nights","room nights","住宿夜数","凌晨入住"]} -->

# Hotel Night and Room Accounting

## Activate and limit the scope

Use when the traveler could book the wrong local night, leave an accommodation gap, or multiply a hotel quote incorrectly. This guide concerns access to lodging and room-night coverage, not calculating an overnight transport journey's elapsed time. An arrival date and a hotel check-in date need not be identical when immediate room access is required.

## Minimum inputs and evidence

Collect local arrival and departure dates and times, the first moment a room is needed, the last moment it is needed, adults and rooms, and essential bed requirements. Check the hotel's current check-in, check-out, early-arrival, late-arrival, and no-show terms, plus the exact offer's dates and occupancy. Use the property or booking operator's applicable policy; “24-hour reception” alone does not establish early room availability or retention of an unused prior night.

## Decision procedure

1. Draw the required accommodation intervals in destination local dates. List every paid night explicitly; checkout is the boundary after the last night, not another occupied night by default.
2. Match room access to those intervals. If immediate early-morning access requires the preceding hotel night, verify late-arrival handling and retention directly through an authorized user action. Otherwise plan a confirmed luggage or waiting arrangement until normal access.
3. Check rooms, adult occupancy, and beds separately. Multiply a per-room-per-night quote by confirmed rooms and nights only when that quote applies throughout. A full-stay total must not be multiplied again.
4. Separate day-use, late checkout, taxes, and deposits where relevant. Recheck continuity when a property change or date change splits the stay.

## Existing fields, gate, and fallback

Bind lodging events with `lodging_id` to `planning.lodging_options[]`. Match `room_requirement` against hotel snapshot `query.requested_occupancy`; existing hotel queries retain `check_in_date` and `check_out_date`. Preserve quoted `price.amount`, `currency`, `basis`, and `display` within source snapshots and use `inventory_refs[]` for the selected offer. Summarize room access and the explicitly counted nights in event `details` and `cost_summary`; use `readiness` for unresolved property confirmation. See [lodging and arrival checks](../trip-readiness.md).

Do not claim multi-room availability from a quotation that lacks that capacity verification.

## Synthetic decision change

A traveler arrives at 01:00 on the 12th and wants immediate room access through checkout on the 14th. Subject to verified late-arrival retention, the stay may require the nights of the 11th, 12th, and 13th: three nights. For two rooms that is six room-nights, not the four implied by entering check-in on the 12th.
