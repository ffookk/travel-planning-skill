<!-- travel-guide: {"id":"low-connectivity-travel","title":"Travel with Limited Connectivity","category":"readiness","when":"A planned leg may lack the data connection needed for navigation, admission, or coordination.","tags":["offline travel","connectivity","离线出行","弱网准备"]} -->

# Travel with Limited Connectivity

## Activation and limits

Use this guide when loss of mobile data would break a specific step in the itinerary. It is not a promise of offline navigation, emergency coverage, or universal ticket access. A locally saved itinerary may still contain links, map functions, or images that need a connection.

## Minimum functional inputs

Collect the affected legs, expected connection gaps, which traveler-operated devices will be available, and the functions that must work without data. Ask whether a printed or locally saved alternative is acceptable. Do not request account credentials, SIM identifiers, device identifiers, ticket codes, or browser-session exports.

## Decision procedure

1. List connection dependencies at the point of use: finding an entrance, showing admission, receiving a pickup change, opening a hotel door, paying, or finding the reunion point. Distinguish a static address from live inventory or a changing authentication code.
2. Check each operator's official offline process. Confirm whether its ticket or reservation must be loaded in advance, whether screenshots are accepted, and whether an account or refreshed code is needed. Do not copy a barcode or session-bearing link into the itinerary to work around an unresolved process.
3. Prepare permissible local resources using the relevant app's supported features and the traveler's own private storage. Include human-readable station names, exact entrances, key written directions, and destination local dates and times. Keep identity-bearing tickets separate from the shareable plan.
4. Have the traveler test required functions without a connection before the affected leg. Describe the observed result and its exact scope in the readiness summary: a completed successful traveler check can use `status=verified` for that tested function; a failed or unperformed required check uses `status=to_recheck` with an official HTTPS action link and the next action. Use `estimated` only for an identified estimate, and `not_applicable` only when the function is not needed. Do not invent `pass` or `unresolved` status values, or claim a check occurred merely because a file downloaded successfully.
5. Define a usable alternative for each failed dependency, such as an operator-confirmed staffed entry point or a prearranged public meeting location. Verify operating hours and payment options. If the essential step has no viable fallback, change that dependency before finalizing the leg.

## Record and fallback

Put the dependency checks in `planning.readiness[]` with official evidence and recheck actions. Record exact entrance and exit instructions in the existing attraction execution fields. For attraction events, put local-file preparation and pre-visit checks in `preparation[]`, point-of-use actions in `execution.checkpoints[].instruction`, and the overall alternative in `execution.fallback`; attraction `details` and `tips` are not rendered. Non-attraction events may use `details` and `tips` for those reminders. A booking or advance arrangement belongs in `planning.booking_tasks[]`. Use [trip readiness](../trip-readiness.md) and [interactive-page guidance](../interactive-page.md), without implying that this guide adds an offline-map or secure-ticket feature.

## Synthetic decision example

A fictional museum uses a code that must refresh online, while the traveler expects no data at its entrance. The operator confirms a staffed alternative open during the visit, with a private verification procedure. Route the event to that entrance and add a traveler preparation task. If that alternative is unavailable, keep admission unresolved rather than presenting a saved screenshot as sufficient.
