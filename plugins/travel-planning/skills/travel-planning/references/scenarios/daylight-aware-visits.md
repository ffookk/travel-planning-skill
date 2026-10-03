<!-- travel-guide: {"id":"daylight-aware-visits","title":"Daylight-Aware Visits","category":"planning","when":"Use when the purpose or practical completion of an outdoor visit depends on daylight, twilight, sunrise, or sunset at the selected location and date.","tags":["daylight","sunset","日照","日落"]} -->

# Daylight-Aware Visits

## Activate and limit the scope

Use for a daylight-dependent viewpoint, outdoor circuit, photography stop, or return path. Skip when daylight does not change the activity decision. This guide concerns available light and execution timing; seasonal service availability is checked separately. Sunset alone does not establish safe walking conditions, legal access, or a guaranteed visible sunset.

## Minimum inputs and evidence

Collect the actual viewpoint and exit, date, local timezone, desired light condition, researched visit and return durations, and the traveler's acceptable walking conditions. Use a reliable astronomical or meteorological source for that place and date. State whether the value is sunrise, sunset, or a specified twilight definition. Separately verify operator access hours, exit rules, return transport, and local warnings. Terrain, buildings, and weather can change what is visible before the published astronomical time.

## Decision procedure

1. Identify what must occur in daylight: the view, a particular path segment, or the entire return. Avoid turning a preference for evening light into a late finish without checking the exit.
2. Work backward from the earliest applicable constraint: an official path closure, transport departure, or the traveler's chosen daylight limit. Use researched movement durations and an explicitly stated planning margin; do not invent a universal safety buffer.
3. Compare arriving earlier, shortening a nonessential checkpoint, or selecting an accessible alternative viewpoint. A later sunset cannot override an earlier official closure.
4. Recheck weather and warnings near the visit. Poor visibility may remove the photography benefit without making the whole attraction unsuitable; choose the fallback according to the purpose of the visit.

## Existing fields, gate, and fallback

Record light-dependent reasoning in attraction `best_time` and `best_time_reason`. Place actual times in the event and `execution.checkpoints[]`, with `execution.leave_by`, `execution.exit`, and a researched `fallback`. Keep weather evidence in `planning.weather[]` linked through `weather_id`; astronomical timing evidence can use `sources[]` and `claims[]`. Preserve local date and timezone in the explanation using [existing event fields](../itinerary-schema.md); this guide adds no astronomical calculator.

Without reliable timing or a workable return, choose a daytime visit or a different viewpoint. Do not label an unverified dark return as safe.

## Synthetic decision change

For a fictional visit, sunset is 17:40, but the operator closes the return path at 17:20. A researched 25-minute return means leaving the viewpoint before 16:55, with any chosen margin stated separately. The itinerary moves the viewpoint earlier instead of scheduling a 17:30 sunset stop that cannot use the confirmed exit.
