<!-- travel-guide: {"id":"step-free-routing","title":"Continuous Step-Free Routes","category":"readiness","when":"A selected journey must avoid steps across every transfer and entrance.","tags":["step-free","accessibility","无台阶","无障碍换乘"]} -->

# Continuous Step-Free Routes

## Activation and limits

Use this guide when one broken link, such as a station stairway or inaccessible entrance, would make the selected route unusable. It complements [trip readiness](../trip-readiness.md). It does not certify accessibility, assess a person's abilities, or assume that an accessibility symbol covers an entire journey.

## Minimum functional inputs

Ask which barriers must be avoided: steps, steep gradients, uneven surfaces, unsupported transfers, or long standing periods. Obtain the travel date, actual origin and destination entrances, acceptable modes, and assistance preferences. Request equipment dimensions only when an operator needs them to determine compatibility; do not request a diagnosis, identity document, or medical history.

## Decision procedure

1. Break the journey into continuous links: departure door, street approach, station entrance, platform access, boarding, interchange, arrival platform, exit, and destination entrance. Include the return journey independently.
2. Check the responsible operator's current accessibility information for each link. Resolve the exact entrance, lift operating period, maintenance notices, boarding arrangements, assistance booking conditions, and any published equipment restrictions. A map showing a lift does not establish that it operates on the travel date.
3. Classify each essential link as supported by dated evidence or unresolved. Keep conditional requirements explicit, such as assistance that still needs traveler confirmation. Do not promote the whole route to verified because its longest leg is accessible.
4. Evaluate a complete alternative chain before adopting it. A different station exit may add a crossing or slope; an alternative vehicle may require its own compatibility check. Include evidenced waiting and transfer time rather than inventing a universal buffer.
5. Before departure, recheck the links whose failure would change the route. If a required link remains unresolved, select an evidenced alternative or leave the affected visit unconfirmed.

## Record and fallback

Keep evidence, limitations, and the next check in `planning.readiness[]`, with `source_ids`, `checked_at`, and actionable HTTPS links for `to_recheck`. Use existing transport records for the selected legs. Record actual attraction entry and exit in `execution.entry` and `execution.exit`; put the relevant action in checkpoint `instruction`. Assistance reservations belong in `planning.booking_tasks[]`. Follow the [existing itinerary contract](../itinerary-schema.md), without adding a new accessibility schema.

## Synthetic decision example

In a fictional plan, Station A's east lift is unavailable on the visit date. Its west exit has no confirmed continuous route to Museum B. A separately researched bus route has a confirmed boarding arrangement and a level approach to the museum's designated entrance. Select that complete route; retain the station option as `to_recheck`, not as the automatic fallback.
