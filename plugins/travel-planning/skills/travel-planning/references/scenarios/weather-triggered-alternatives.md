<!-- travel-guide: {"id":"weather-triggered-alternatives","title":"Weather-Triggered Alternative Plans","category":"readiness","when":"Weather or an official operating notice could require replacing a selected outdoor activity.","tags":["weather alternatives","operating notices","天气备选","停运替代"]} -->

# Weather-Triggered Alternative Plans

## Activation and limits

Use this guide when a specific weather-sensitive activity needs an executable replacement. It does not define universal wind, heat, rain, or visibility limits. Apply the responsible authority's or operator's current instructions, together with traveler-stated preferences; a forecast is not an operating guarantee.

## Minimum functional inputs

Collect the affected activity and time, essential onward commitments, traveler preferences that change selection, and acceptable replacement types. Establish which reservations are flexible and what cancellation terms are evidenced. No medical explanation for a preference is needed.

## Decision procedure

1. Identify the actual dependency: vessel operation, exposed approach, site access, outdoor visibility, or an activity-specific restriction. Determine which operator or authority controls that dependency, rather than relying only on a generic city forecast.
2. Research both the main option and a plausible replacement for the same date and execution window. Verify the replacement's opening, entry requirements, availability, route, and return to the next commitment. “Indoor” alone does not establish access or eliminate weather disruption.
3. Define a decision trigger in plain language tied to an official notice, an operator announcement, or a traveler-selected preference. Record when that information becomes useful to the booking or departure decision. Do not invent a fixed numerical safety cutoff.
4. Check the latest applicable notice before committing to the affected leg. If sources disagree, preserve the disagreement and seek clarification; a favorable forecast does not override an operator closure.
5. On a switch, update the selected event, attraction and transport references, meal anchors, and daily route. Recheck timing and costs. Preserve an unused reservation's actual cancellation status without implying that a task cancels it. Material route changes still require user approval.

## Record and fallback

Use `planning.weather[]` for sourced weather information and the existing event `weather_id` link. Put the actionable on-site alternative in the relevant `execution.checkpoints[]`; keep source and booking evidence in each attraction's existing records. Use `planning.readiness[]` for the decision trigger and unresolved dependency, with `to_recheck` and a specific official HTTPS action link when necessary. `planning.booking_tasks[]` can hold the required recheck or reservation action. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md); do not place mutually exclusive alternatives into the same executed route.

## Synthetic decision example

A fictional harbor operator cancels an afternoon departure. Museum B is an indoor candidate, but its available entry is later than the onward train permits. Reject B as that day's replacement. Use an independently checked nearby gallery that fits the remaining window, or retain a free period if no suitable visit is established. Do not shorten the train transfer to rescue the museum option.
