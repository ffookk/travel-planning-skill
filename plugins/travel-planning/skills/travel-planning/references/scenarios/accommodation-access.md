<!-- travel-guide: {"id":"accommodation-access","title":"Accommodation Access by Actual Room","category":"readiness","when":"A lodging choice depends on specific access features being available in the room and route actually booked.","tags":["accessible accommodation","room features","住宿无障碍","客房适配"]} -->

# Accommodation Access by Actual Room

## Activation and limits

Use this guide when a property-wide accessibility label is insufficient to choose lodging. It does not certify a building, determine personal suitability, or assume that staff can provide physical assistance. Property identity, room inventory, and functional access are separate questions.

## Minimum functional inputs

Collect dates, room and party counts, required bed arrangement, and the specific features needed to use the property. Examples include a step-free entrance, a usable lift, a particular bathroom arrangement, or independent access after reception closes. Ask for dimensions only when they decide compatibility. Do not request a diagnosis, identity document, or personal care history.

## Decision procedure

1. Trace the actual arrival-to-room chain, including vehicle drop-off, entrance, reception, lifts, corridors, room, and necessary shared facilities. Check departure access as well. An accessible lobby does not establish an accessible room route.
2. Match each required feature to the exact room category and dates. Use property information and a specific confirmation route; distinguish measured descriptions from marketing language or a platform's general accessibility filter.
3. Establish whether the required room is bookable as a guaranteed category or merely an allocation request. Verify party capacity and bed configuration independently. A quote for a standard room cannot establish availability of the required accessible room.
4. Check arrangements that depend on service hours, including late arrival, lift access, support requests, and any relevant published emergency assistance procedure. Do not infer that an evacuation arrangement or physical assistance exists because reception is staffed.
5. Compare a second usable property or room arrangement using the same requirements. If an essential feature or allocation remains uncertain, keep the choice conditional and resolve it before a booking commitment. Do not equate a refundable rate with confirmation that the room is suitable.

## Record and fallback

Keep identity, occupancy, dates, and quote evidence in `planning.lodging_options[]` and its existing inventory references. Record feature-specific evidence and allocation uncertainty in `planning.readiness[]`, referencing sources and the relevant lodging ID in its summary. Use `planning.booking_tasks[]` for a required room confirmation, and lodging event `details` or `tips` for arrival instructions. A `to_recheck` item needs an official HTTPS action link. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md); do not upgrade location or inventory verification to mean functional suitability.

## Synthetic decision example

A fictional hotel confirms a step-free route and a suitable bathroom only for Room Category R. The available quote covers Category S, while R is request-only. Keep the property as a candidate with unresolved allocation. Compare another property with evidenced availability in a suitable category; do not describe the first quote as an accessible-room offer.
