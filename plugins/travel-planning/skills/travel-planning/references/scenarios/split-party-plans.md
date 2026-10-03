<!-- travel-guide: {"id":"split-party-plans","title":"Temporary Split-Party Plans","category":"readiness","when":"Travelers on one trip deliberately choose different activities before a planned reunion.","tags":["split party","rendezvous","分组出行","集合安排"]} -->

# Temporary Split-Party Plans

## Activation and limits

Use this guide for a deliberate, temporary separation with an agreed reunion. It is not a missing-person procedure and does not decide who may travel independently. The travelers establish supervision and assistance arrangements; do not assume that a child or dependent traveler can form an independent subgroup.

## Minimum functional inputs

Collect anonymous subgroup counts, activities, required accompaniment, independently usable transport, shared resources, and the latest acceptable reunion. Ask whether each subgroup can navigate without mobile data. Use role labels such as “Group A”; do not collect names, personal phone numbers, or live location feeds.

## Decision procedure

1. Fix the common departure and reunion anchors before researching separate activities. Choose a precise public meeting point with a usable entrance and opening period, not a large district or a station name alone.
2. Check each subgroup's entire branch: admission, transport, exit, and travel to the reunion point. Recalculate ticket quantities and room or vehicle use where separation changes them; a shared booking may not permit separate entry or boarding.
3. Identify shared dependencies, including a single key, payment method, mobility support, or stored belongings. Ask the travelers to resolve these privately before making either branch executable.
4. Agree a traveler-operated check-in and a missed-reunion rule that works offline. Specify destination local time, a primary point, a fallback point, and what each group does if the primary closes. Keep the rule simple enough that both groups do not search for each other along different paths.
5. If one branch cannot reliably meet a hard onward departure, shorten it, change the reunion, or keep the party together. Do not hide the conflict inside an estimated transfer.

## Record and fallback

The [existing itinerary schema](../itinerary-schema.md) has one ordered event stream and at most one daily route per date; it does not model concurrent subgroup schedules. Use separate standard-format itineraries for the branches, or keep the common itinerary limited to the common program and explain optional branches in `details`. Do not combine simultaneous legs into one route or imply that descriptive text is a validated parallel schedule. Record the reunion rule and unresolved dependencies in `planning.readiness[]`; use ordinary events in each branch and booking tasks for its own commitments. Follow [trip readiness](../trip-readiness.md) for evidence and privacy.

## Synthetic decision example

Group A visits a fictional gallery while Group B takes a harbor walk. Both branch plans end at Library C's named public entrance at 16:00 local time. Its closure fallback is a separately checked public square. The gallery ticket requires all ticket holders to enter together, so create a subgroup-sized booking task instead of reusing the whole-party ticket assumption.
