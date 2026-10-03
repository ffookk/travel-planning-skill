<!-- travel-guide: {"id":"local-transport-ticketing","title":"Local Transport Ticket Selection","category":"planning","when":"Use when a local itinerary could use different tickets, passes, or payment methods whose eligibility and coverage change cost or boarding feasibility.","tags":["transit fares","passes","本地交通票","交通通票"]} -->

# Local Transport Ticket Selection

## Activate and limit the scope

Use when local journeys cross operators, zones, validity periods, or special-fare services, or when a pass is being compared with individual fares. Skip if one straightforward verified fare already covers the planned movement. This guide chooses a usable ticket product; it does not forecast service reliability or install, fund, or register a payment account.

## Minimum inputs and evidence

Collect the planned journeys and dates, operators and zones, traveler eligibility categories, relevant luggage needs, and whether the traveler can use the required physical or digital ticket. Check each operator's current fare and conditions pages. Establish activation timing, duration, transfer rules, excluded routes, validation requirements, and any mandatory supplement or card cost. Do not infer a concession from age alone without the required residency or identification conditions.

## Decision procedure

1. Map each planned leg to the product that actually covers it. Pay particular attention to airport, express, ferry, and inter-operator legs where ordinary coverage may not apply.
2. Compare the eligible single-fare baseline with the pass, adding verified mandatory supplements and acquisition charges. Count only journeys the itinerary is likely to execute; optional sightseeing rides do not automatically justify a pass.
3. Check the validity clock. A calendar-day product, a rolling duration from activation, and a product valid only on specified dates are not interchangeable. Verify whether the same payment medium must be used consistently for transfers or caps; do not generalize between operators.
4. Confirm how the traveler obtains and validates the ticket before the first required boarding. If that step cannot be completed using available means, retain an operator-supported alternative even if it costs more.

## Existing fields, gate, and fallback

Put fare coverage and validation instructions in the selected `transport_edges[]` object's `cost`, `route`, and `action_links[]`, and the transport event's `details`. Use event `cost_items[]` and `cost_summary` to count a selected pass once and identify which legs it covers; do not also charge those covered single fares. A `planning.readiness[]` item can hold an unresolved eligibility or acquisition check. Follow [transport data rules](../itinerary-schema.md).

If eligibility or exclusions remain unknown, compare using known eligible fares and mark the pass conditional. Planning does not authorize purchase or account setup.

## Synthetic decision change

A fictional day pass costs 12 units; three planned rides cost 3 each. The airport express additionally requires 8 units under either choice. The comparison is 20 with the pass versus 17 without, not 12 versus 17. The itinerary keeps individual fares unless the actual ride plan changes.
