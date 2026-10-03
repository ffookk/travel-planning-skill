<!-- travel-guide: {"id":"multi-currency-budget","title":"Multi-Currency Planning Budget","category":"planning","when":"Use when an itinerary contains costs in more than one currency and the traveler needs a common-currency planning view.","tags":["currency","exchange rate","多币种预算","汇率"]} -->

# Multi-Currency Planning Budget

## Activate and limit the scope

Use when currency differences prevent a traveler from judging affordability. This guide handles conversion assumptions and budget exposure, not whether two quotes cover the same people, rooms, or inclusions. Establish comparable quote scope before converting. Do not offer exchange-rate forecasts or imply that a planning conversion is the eventual card settlement amount.

## Minimum inputs and evidence

Collect the selected event costs, their original currencies, the user's preferred comparison currency, and a dated exchange-rate source. Identify paid versus unpaid amounts, refundable deposits, and known payment fees without collecting card or account details. Retain the source's rate direction: “one unit of A buys B” is different from its inverse. For actual payment costs, consult the applicable issuer or payment provider's published terms; a reference rate does not establish those fees.

## Decision procedure

1. Group the included costs by original currency. Remove duplicates such as a pass and the single tickets it replaces. Keep optional activities and unresolved amounts outside the committed baseline.
2. Label the conversion date, source, direction, and calculation. Multiply or divide consistently. Preserve the original amount beside every converted estimate so a later rate update can be traced.
3. Present separate currency subtotals and a clearly labeled comparison total. Keep deposits and potential cancellation exposure distinct from expected spending; do not count a returned deposit as an expense or ignore its temporary cash requirement.
4. If exchange-rate movement would change the selected option, show a small user-agreed sensitivity range rather than a prediction. Refresh the comparison when major unpaid costs or the rate basis changes.

## Existing fields, gate, and fallback

Keep original quote evidence in `planning.source_snapshots[].items[].price` using the existing `amount`, `currency`, `basis`, and `display` fields. Event `cost_items[]` retain currency labels in `unit_price` and `subtotal`; `cost_summary` may explain the derived comparison, its date, and exclusions. Record rate evidence in `sources[]` and `claims[]`. Follow [budget derivation rules](../itinerary-schema.md); this guide introduces no conversion engine or mandatory currency fields.

Without a defensible rate, deliver original-currency subtotals and a `readiness` recheck action, not an invented common total.

## Synthetic decision change

Two selected costs are EUR 100 and GBP 80. Using explicitly hypothetical rates of 1.5 and 1.8 units of the comparison currency gives 150 + 144 = 294, not 180. Against a comparison budget of 280, the traveler removes an optional activity. The rates illustrate arithmetic only and are not current quotations.
