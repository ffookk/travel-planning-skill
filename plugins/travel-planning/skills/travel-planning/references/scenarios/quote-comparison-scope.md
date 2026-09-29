<!-- travel-guide: {"id":"quote-comparison-scope","title":"Comparable Quote Scope","category":"planning","when":"Use when candidate prices appear comparable but differ in party coverage, duration, quantity, included services, or mandatory charges.","tags":["quote scope","inclusions","报价口径","费用包含项"]} -->

# Comparable Quote Scope

## Activate and limit the scope

Use before ranking transport, admission, lodging, or package candidates by price. A smaller displayed number is not a cheaper feasible option until its scope matches the trip. This guide normalizes coverage and inclusions; currency conversion and cancellation deadlines require separate decisions after the scope is understood.

## Minimum inputs and evidence

Collect the requested people and relevant age categories, rooms or vehicles, dates and nights, required baggage or equipment, product class, and mandatory services. For each candidate retain the exact operator or seller offer, query conditions, quoted unit, tax treatment, availability evidence, and inclusions or exclusions. Obtain age and occupancy eligibility from the applicable operator rather than inferring them from a generic “family” or “standard” label.

## Decision procedure

1. State a common comparison requirement before looking at totals. For example, two adults, one transfer, two suitable bags, and the same pickup and drop-off points.
2. Expand each quote using its actual unit: per person, room-night, vehicle, package, or full stay. Do not multiply a party total by party size, or treat a vehicle's advertised capacity as a confirmed fit for its luggage.
3. Add only mandatory extras supported by evidence. Separate known extra amounts from unknown charges. Keep optional comfort upgrades outside the comparable baseline.
4. Compare feasible offers first, then price. Record when a cheaper headline offer fails capacity, required service, or operating conditions. A platform result is a candidate quotation, not a held place.

## Existing fields, gate, and fallback

Retain supplier-neutral quote evidence in `source_snapshots[].items[].price`, and bind selected transport or lodging through `inventory_refs[]`. Use event `cost_items[]` with explicit `unit_price`, `quantity`, `subtotal`, `pricing_role`, `required`, `status`, and `source_ids`. Explain the covered party and omissions in `cost_summary`. Preserve native quote text rather than inventing provider fields; [the data contract](../itinerary-schema.md) governs exact structures.

If an essential inclusion or quantity is unknown, mark the option `to_recheck` with a specific official query. Do not declare it the lowest comparable price. Keep a fully scoped fallback even if its headline price is higher.

## Synthetic decision change

A fictional shuttle advertises 30 currency units per adult and charges a confirmed mandatory 10 per checked bag. For two adults with two bags, its comparable total is 80. A private transfer at 75 for the whole vehicle includes both bags. Once the capacity and route match are verified, the 75-unit option becomes cheaper despite its larger headline number.
