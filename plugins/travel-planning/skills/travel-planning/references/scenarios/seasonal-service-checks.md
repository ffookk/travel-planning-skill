<!-- travel-guide: {"id":"seasonal-service-checks","title":"Seasonal Service Dependency Checks","category":"planning","when":"Use when a selected attraction or route depends on a seasonal, weekend-only, maintenance-sensitive, or condition-dependent service.","tags":["seasonal service","maintenance","季节运营","停运","weekend shuttle","seasonal ferry","lift","guided access","周末接驳","季节渡轮","缆车","导览准入"]} -->

# Seasonal Service Dependency Checks

## Activate and limit the scope

Use for a lift, ferry, shuttle, guided access, visitor facility, or route whose operating season affects feasibility. Do not apply a generic “summer” label to all services at a destination. Daylight planning is a separate concern: long daylight does not establish that a seasonal service runs.

## Minimum inputs and evidence

Collect the exact service, operator, boarding and exit locations, travel date, intended direction, latest required return, and what becomes impossible if it does not run. Obtain the operator's current season calendar, service-day pattern, maintenance notice, booking conditions, and dated updates. Check whether a calendar describes announced operations, a historical season, or a tentative opening subject to conditions. Community reports can identify a likely issue but do not confirm current operation.

## Decision procedure

1. Trace the dependency chain. The destination may be open while its only practical connection is not, or outbound service may exist without the needed return.
2. Match the exact trip date against season boundaries, weekday exceptions, maintenance periods, and relevant condition notices. Review each independently rather than copying an entire route as “seasonal: verified.”
3. Calculate whether the confirmed operating interval supports the intended visit and return. Distinguish last boarding, last departure, and final arrival; use the operator's terminology.
4. If dates are not published, preserve the route as conditional and define when it must be reconsidered before related commitments. Investigate an alternate operating service or another destination with independent access. A physically possible footpath is not automatically an acceptable replacement.

## Existing fields, gate, and fallback

Use `planning.readiness[]` for season checks, including `status`, `deadline`, `checked_at`, `source_ids`, and an official `action_links[]` query. Carry service consequences into transport `route`, `door_to_door_duration`, `fallback`, and attraction `admission.notice` or `execution.fallback`. Keep relevant sources and field-level uncertainty through [the evidence rules](../source-strategy.md). Use supported inventory snapshots only where that provider and product type already fit the snapshot contract.

Do not label a dependent final sequence confirmed while the essential service remains unresolved. Prefer a complete fallback that works without it, and state the trigger for switching.

## Synthetic decision change

A fictional lakeside attraction is open on Tuesday, but its seasonal shuttle runs only on weekends during that month. A route built around a Tuesday shuttle is infeasible despite the attraction's opening calendar. With no verified suitable alternative, move the visit to Saturday or replace it with an independently accessible attraction.
