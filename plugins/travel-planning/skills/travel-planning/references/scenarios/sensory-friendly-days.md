<!-- travel-guide: {"id":"sensory-friendly-days","title":"Days with Manageable Sensory Exposure","category":"readiness","when":"The traveler wants specific noise, lighting, crowd, or enclosure conditions to shape the day.","tags":["sensory needs","quiet spaces","感官友好","安静休息"]} -->

# Days with Manageable Sensory Exposure

## Activation and limits

Use this guide when particular environmental conditions affect which activities or sequences the traveler can comfortably choose. It does not diagnose a condition, prescribe coping methods, or promise a quiet environment. A venue's advertised quiet session is evidence about its arrangements, not a guarantee about every visitor or space.

## Minimum functional inputs

Ask which conditions to avoid or limit, which are tolerable with an easy exit, preferred visit length, and whether the traveler wants advance descriptions or spontaneous choices. Collect desired retreat features, such as seating or outdoor space, without requesting a diagnosis or personal incident history. Establish whether queues and enclosed transport are also relevant.

## Decision procedure

1. Inspect the full experience, including security, queues, lifts, compulsory introductory films, amplified announcements, and the route out. A calm main gallery can still have an unsuitable approach.
2. Verify venue-published session dates, lighting or sound adjustments, admission arrangements, re-entry rules, and availability of a retreat space. Check whether assistance or a special session requires a reservation. Community descriptions can identify questions; label them as observations rather than official guarantees.
3. Compare options by controllability: an optional room with a nearby exit differs from a timed performance with restricted departure. Apply the same constraints to every approach, inter-venue, and return leg, including platforms, tunnels, enclosed vehicles, and exits. Compare an evidenced acceptable route and fallback; a suitable venue does not make an enclosed transfer acceptable. Recheck timing if the selected mode or path changes. Prefer the option that satisfies the traveler's stated conditions, not a generic “sensory-friendly” label.
4. Sequence demanding sections with traveler-chosen recovery opportunities. Check that the proposed retreat is open and reachable when needed; a closed café or distant park is not an executable pause.
5. Define a simple traveler-controlled switch before entering: skip a section, shorten the visit, or take the researched alternative if the observed conditions are unsuitable. Do not require the traveler to justify using it.

## Record and fallback

Record functional conditions and unresolved venue questions in `planning.readiness[]`. Put the selected entrance, exit, and on-site choices in attraction `execution` checkpoints; use ordinary `rest` events for pauses between venues. Keep an alternative's opening and admission evidence in its attraction record. Store selected map-supported legs and their researched fallback in `planning.transport_edges[]`, and bind the transport events through `route_id`; use the existing intercity option when that is the event's referenced service. Record unresolved route conditions in readiness rather than assuming a mode is acceptable everywhere. `details` and `tips` can explain the choice but must not replace execution fields. Use [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md); retain `to_recheck` with an actionable official HTTPS link when arrangements are unclear.

## Synthetic decision example

A fictional aquarium offers a quiet morning session, but its official description still includes a compulsory amplified briefing. A nearby gallery permits independent entry and departure. The traveler excludes amplified briefings, so select the gallery and an optional courtyard pause. Keep the aquarium as a future candidate pending clarification, without describing either venue as universally suitable. If the traveler also excludes enclosed rail travel, replace the gallery's proposed subway approach only after verifying an acceptable surface route and its timing; selecting the gallery alone does not resolve that transport constraint.
