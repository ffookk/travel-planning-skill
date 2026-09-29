<!-- travel-guide: {"id":"overnight-transfers","title":"Overnight transfer and arrival-date planning","category":"transport","when":"Use when a connection or arrival crosses midnight and depends on overnight access, accommodation, or an early onward departure.","tags":["overnight","midnight arrival","凌晨抵达","过夜中转"]} -->

# Overnight transfer and arrival-date planning

## Activate for an actual overnight dependency

Use this guide for a midnight arrival, an overnight connection, or a departure that makes the previous night's location important. An ordinary evening journey with confirmed accommodation and no overnight access dependency does not need this extra analysis.

Request only the local arrival and departure dates, required sleep window, luggage needs, and whether the traveler is willing to leave the terminal. Keep booking references and personal document details out of the plan. Distinguish the calendar date of physical arrival from the accommodation night being purchased.

## Verify the usable night

Check airport or station overnight access for the particular terminal and area, including whether arriving passengers may remain there. Verify any landside transition and applicable entry requirements through official channels. An open airport does not establish that a specific waiting area, security checkpoint, lounge, or transfer service remains accessible.

For accommodation, obtain the property's answer for the actual arrival time: which reservation night covers it, whether a late-arrival notice is needed, and when entry becomes possible. Verify early-morning transport independently from daytime service. Calculate the usable rest interval after arrival processing and travel, then subtract the time needed to return for the next service's applicable deadline.

## Choose and record

If a planned waiting location is inaccessible, replace it with a confirmed accessible location or change the journey. Do not describe an unverified lounge, chair, or early check-in as a booked room. If the remaining rest interval is below the traveler's stated minimum, offer a later departure or an overnight stay with a longer interval; make the schedule tradeoff visible.

Use `planning.readiness[]` for overnight access and late-arrival confirmation. Create a `planning.booking_tasks[]` item only for the room or transfer that must be secured. Record arrival and return access in `planning.transport_edges[]`. Place departure and arrival events on their correct `day.date`; use `event.details` for local dates, time zones, and the covered accommodation night. Put the access-failure alternative in `event.tips`. Follow the [existing date and event contract](../itinerary-schema.md), without inventing a time such as 24:40.

## Synthetic worked scenario

Arrival is 00:40 on 8 May, with onward boarding required at 05:40. Suppose the operator confirms the waiting area closes from 01:30 to 04:30. Waiting there is removed from the plan. A nearby property's verified entry at 01:30 and required departure at 04:30 provide only three hours on site, less than the traveler's four-hour rest requirement. The decision changes to a later onward service, with the room's reservation night confirmed directly before purchase.
