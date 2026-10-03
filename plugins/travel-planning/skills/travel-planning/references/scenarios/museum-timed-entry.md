<!-- travel-guide: {"id":"museum-timed-entry","title":"Museum Timed-Entry Sequencing","category":"planning","when":"Use when a museum visit combines general admission with a dated entry slot, exhibition, guided session, or other separately constrained access.","tags":["museum","timed entry","博物馆","分时入馆"]} -->

# Museum Timed-Entry Sequencing

## Activate and limit the scope

Use when “the museum is open” is insufficient to establish access to the intended experience. Skip for an unconstrained drop-in visit with no relevant special access. This guide sequences admitted activities after a session is identified; it does not calculate when tickets go on sale or assume that holding general admission grants exhibition access.

## Minimum inputs and evidence

Collect the museum, target date, intended galleries or exhibition, party eligibility, booked or proposed session, preferred visit duration, and arrival route. Read the museum's official rules for general entry, special exhibitions, tours, security screening, bag restrictions, re-entry, last admission, and gallery closing. Distinguish a displayed session from a booking the user has actually confirmed. Record only the confirmation status needed for planning, not ticket barcodes, order identifiers, or visitor names.

## Decision procedure

1. Build the access dependencies: building entry, security or bag storage, exhibition access, and any guide meeting point. Confirm whether the same ticket covers each dependency.
2. Place the timed component first. Work backward through researched approach and screening requirements, then forward through the user's priority galleries and the next commitment.
3. Check whether a stated late-arrival allowance actually applies to that product. Do not infer a grace period from another museum or an anecdote. Verify whether leaving the building invalidates re-entry before inserting lunch outside.
4. If the desired components do not fit, remove a lower-priority gallery, change the session, or split the visit. Never compress a fixed guided session or ignore last admission to retain every stop.

## Existing fields, gate, and fallback

Use an attraction event's `admission` for researched `opening_hours`, `last_entry`, `reservation_method`, and `entry_requirement`. Represent entry, exhibition, rest, and exit through ordered `execution.checkpoints[]`; set `leave_by` and a specific `fallback`. Bind session actions with `booking_task_ids[]` and `planning.booking_tasks[]`, including `target_date`, `target_session`, `product`, `quantity`, and truthful `status`. Distinguish general tickets and optional supplements in `cost_items[]`. See [attraction research](../research-workflow.md).

The selected sequence needs every required access dependency resolved. If exhibition access remains unavailable, present general galleries as a distinct fallback rather than promising the exhibition.

## Synthetic decision change

A fictional museum opens at 10:00 and offers an 11:00 exhibition slot. The museum's own instructions require arrival at the exhibition entrance 15 minutes before that slot. A plan reaching the building at 10:50 cannot satisfy the approach and screening sequence. Move arrival earlier or choose a later exhibition; the general opening time does not rescue the original plan.
