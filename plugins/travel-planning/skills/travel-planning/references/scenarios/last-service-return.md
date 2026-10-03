<!-- travel-guide: {"id":"last-service-return","title":"Last-service return cutoffs","category":"transport","when":"Use when an attraction or evening activity relies on the last practical scheduled service back to accommodation or another fixed destination.","tags":["last bus","last train","末班车","返程截止"]} -->

# Last-service return cutoffs

## Activate for a fragile final service

Use this guide when the final bus, train, shuttle, or ferry is the only verified way back within the traveler's limits. It is unnecessary when frequent service continues comfortably beyond the visit and a workable alternative is already established. A geographically nearby stop is not enough: confirm the correct route and direction.

Ask for the destination that must be reached, the latest acceptable arrival, walking constraints, and the budget or willingness to use an alternative. A hotel neighborhood or public meeting point is usually enough during comparison; avoid sharing a private residential address.

## Verify the departure that actually matters

Use the operator's timetable for the travel date, direction, stop, and service calendar, then check relevant notices. Resolve holiday variations, reservation or boarding requirements, and departures after midnight against the operator's date convention. Do not silently turn a Friday-night service into a Saturday-evening option.

Check the walking route from the attraction's actual exit to the boarding point. Include internal exit time where it precedes that walk. A stated closing time or show end may leave no time to reach the final service. Verify the alternative independently: operating hours, pickup point, party capacity, and an acceptable estimated cost. An app icon does not establish available vehicles.

## Choose and record

Work backward from the required boarding time, subtracting exit, walking, and the chosen contingency allowance. This becomes the activity's latest leave time. If it precedes the part of the visit the traveler values, change the activity time, choose verified alternate transport, or select accommodation that removes the dependency. Do not keep the full visit and bury the impossible return in a warning.

In `planning.readiness[]`, record the return service and unresolved alternative check. Use `planning.booking_tasks[]` if the return requires a reserved place. Put the route and fallback in `planning.transport_edges[]`. For an attraction, put the actual exit in `execution.exit`, the cutoff in `execution.leave_by`, and the leave instruction in its exit checkpoint. Keep the event end at or before that cutoff. Put the earlier-return trigger, such as a delayed internal shuttle, in `execution.fallback` or the relevant checkpoint instruction; attraction-level `details` and `tips` are hidden in the detailed view. In an assembly plan, use the attraction configuration's `end` for its planned finish, `exit` and `fallback` for those execution fields, and `checkpoint_overrides` for the instruction. When the planned finish precedes the real cutoff, set `overrides.execution.leave_by` to that cutoff: `end="16:50"` with `overrides={"execution":{"leave_by":"17:05"}}` preserves both times. Without this override, assembly copies `end` into `leave_by`. Non-attraction events may still use `details` and `tips`. Keep evidence and review timing consistent with [trip readiness](../trip-readiness.md).

## Synthetic worked scenario

The last bus departs at 18:05 and requires travelers at the stop by 17:55. Walking from the viewpoint exit takes 35 minutes, and the chosen contingency is 15 minutes. Leave the exit by 17:05. A planned 17:25 light-viewing session cannot fit. Move the session earlier or secure a verified alternate return; do not describe staying through 17:25 as compatible with that bus.
