<!-- travel-guide: {"id":"event-crowd-calendar","title":"Event and Crowd Calendar","category":"planning","when":"Use when a dated festival, match, conference, holiday, or local event may change access, travel time, or the preferred visit sequence.","tags":["events","crowds","活动日历","客流"]} -->

# Event and Crowd Calendar

## Activate and limit the scope

Use when a place or route overlaps a potentially significant dated event. Do not create a citywide event catalogue for every trip, or equate a public holiday with universal closure. Investigate only events that could change the selected itinerary's time, access, transport, or cost.

## Minimum inputs and evidence

Collect the trip dates, selected districts and entrances, fixed appointments, available alternate days, and the traveler's willingness to experience crowds. Check organizer calendars, venue notices, transport operator advisories, and municipal access announcements. Verify the event's location and start/end pattern, not just its city name. Treat recent community reports as experience evidence about congestion or queues; they cannot establish official closures or forecast a precise queue for the trip date.

## Decision procedure

1. Overlay relevant event locations and time windows on the proposed daily route. Include dispersal and setup only where an official notice or defensible local evidence supports them.
2. Classify the effect: a confirmed access restriction, a changed transport service, a plausible crowd increase, or an attractive event the traveler actually wants. Keep the confidence of each effect separate.
3. Compare a different visit time, a different entrance, and a different day. Recheck whether those alternatives preserve timed bookings and meal anchors. Avoid an unverified detour that crosses the same restriction elsewhere.
4. For optional crowd avoidance, explain the tradeoff: an earlier departure, a shorter visit, or losing an event experience. For confirmed access restrictions, replace the affected route rather than adding a vague caution.

## Existing fields, gate, and fallback

Use `planning.readiness[]` for dated calendar checks with `summary`, `status`, `deadline`, `checked_at`, `source_ids`, and `action_links[]`. Update affected attraction `best_time` and `best_time_reason`, transport edge `route` and `fallback`, and actual `days[].events[]`. Keep official restrictions distinct from estimated experience claims in `claims[]`. When an entrance or stop changes, update the actual attraction event's `execution.entry` (and `execution.exit` if affected), including its name and location query. In the same change, update affected `execution.checkpoints[]` names, `instruction`, and `action_links[]` that refer to the old entrance, exit, or approach; the renderer displays these independently of the execution anchors. Preserve unaffected checkpoint content. Update each affected transport edge's `from`/`to`, `map_route.origin`/`destination` coordinates, applicable POI IDs or waypoints, and navigation `action_links[]` together; recheck its door-to-door time. Update `planning.daily_routes[].stops[]` to those same verified anchors. Descriptive route text alone must not leave navigation pointing at the restricted entrance. See [readiness checks](../trip-readiness.md).

An unconfirmed event effect should remain a recheck item, with a route that remains feasible under the stated uncertainty. An old event calendar is a discovery lead, not confirmation of this year's date.

## Synthetic decision change

A fictional race notice closes the bridge on the planned museum approach from 08:00 to 11:00. A 09:30 museum reservation therefore cannot rely on the usual bridge crossing. A verified alternate entrance adds acceptable travel time, so the route changes while the reservation stays. Unverified claims of “huge queues all day” do not justify cancelling the museum.
