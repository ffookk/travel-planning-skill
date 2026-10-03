# Meal execution windows

The audit checks both standalone meal events and attraction checkpoints with `meal_id` against the referenced meal option's researched `time_window`. A single same-day `HH:MM-HH:MM` interval accepts execution exactly at its boundaries. Split, overnight, missing, or approximate window text requires manual rechecking; restaurant opening hours are not substituted for a researched meal window.

Dated execution uses the existing event timing contract. A checkpoint inherits its parent event's timezone, then day and trip settings. When an IANA timezone is known, both endpoints are converted to that zone before comparison; a different end-time representation does not extend the restaurant's researched window. A dated meal must still fit the researched day. Differing endpoint offsets without an IANA zone, and ambiguous or nonexistent daylight-saving window boundaries, remain explicit recheck warnings.

This check uses stored research only. It does not verify live restaurant operations, invent dining duration or transfer buffers, or change the itinerary input. Existing restaurant identity, snapshot, candidate, and route checks remain in effect.
