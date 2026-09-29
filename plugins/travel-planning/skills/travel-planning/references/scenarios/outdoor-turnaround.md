<!-- travel-guide: {"id":"outdoor-turnaround","title":"Outdoor Turnaround Decisions","category":"readiness","when":"An outdoor visit needs an explicit decision point to protect its return route or onward departure.","tags":["turnaround planning","return route","户外折返","返程约束"]} -->

# Outdoor Turnaround Decisions

## Activation and limits

Use this guide for a walking or outdoor sightseeing plan whose optional extent depends on remaining time and a usable return. It is not instruction for technical climbing, remote expeditions, rescue, or assessing terrain beyond the planner's evidence. Qualified guides and responsible authorities determine specialist requirements and operating restrictions.

## Minimum functional inputs

Collect the named route, entry and exit points, required return or transport time, the traveler's stated pace and acceptable scope, and available communication. Ask which optional sections may be dropped. Do not collect medical history or infer capability from age or fitness labels.

## Decision procedure

1. Verify the current route status, access period, closures, exit arrangements, and official visitor guidance for the exact segment. Establish what the published duration includes. A round-trip estimate may exclude queues, shuttle waits, or a different exit.
2. Identify the binding return constraint, such as a site closure, last usable departure, or user-confirmed appointment. Work backward using evidenced return travel and a margin chosen for the actual uncertainty. Label estimates and assumptions; do not impose a universal walking speed or fixed safety allowance.
3. Select identifiable decision points before optional extensions. At each, compare observed progress and current conditions with the remaining return requirement. If the plan no longer supports the return, omit the extension and use the already evaluated exit option.
4. Check whether that exit remains usable under the condition that caused the change. A turnaround instruction is not an instruction to retrace a route that has become hazardous. Follow current authority instructions when access or conditions change.
5. If no credible return estimate, usable exit, or required support can be established, choose a shorter evidenced visit or defer the activity. Do not treat a phone signal, map line, or hoped-for pickup as a verified contingency.

## Record and fallback

Record the route, entrances, exits, and decision actions in the attraction's existing `execution` fields and checkpoint `instruction`. Put predeparture requirements in `preparation[]`; link weather evidence through the existing `weather_id`. Use `planning.readiness[]` for unresolved route or return dependencies with `source_ids`, `checked_at`, and actionable HTTPS links. Selected return legs remain ordinary transport records. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md), without adding an implied safety-rating field.

## Synthetic decision example

In a fictional route, the exit gate closes at 16:00 and the researched return from Junction J takes approximately 90 minutes. This synthetic plan allocates a further 20-minute margin. At 14:00, a 30-minute optional viewpoint extension would exceed that return budget. Omit the extension and use the previously evaluated exit while reassessing current conditions. These times illustrate the calculation; they are not recommended outdoor safety thresholds.
