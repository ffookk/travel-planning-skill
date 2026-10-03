<!-- travel-guide: {"id":"airport-terminal-transfers","title":"Airport terminal transfer paths","category":"transport","when":"Use when a flight connection changes terminal, airport, or security area and the exact passenger path determines feasibility.","tags":["terminal transfer","airside","航站楼换乘","跨机场"]} -->

# Airport terminal transfer paths

## Activate for a physical transfer boundary

Use this guide when the terminal, airport, or airside/landside path changes between flights. Its purpose is to verify the passenger path, not determine which seller protects a missed connection. A confirmed same-terminal transfer with an already documented accessible path needs no duplicate terminal study.

Request flight dates and public service numbers, whether checked bags must be collected, and practical walking or accessibility requirements. Ask only whether necessary boarding documents will be available before transfer. Do not request boarding-pass images, booking codes, or passport details; the traveler can confirm personal entry eligibility privately.

## Verify a continuous permitted path

Use official airport maps and transfer instructions for the specific arriving and departing terminals. Check whether the proposed corridor or shuttle is airside or landside, who may use it, operating hours, boarding location, and any security or border processing required. Confirm the carrier's bag-drop and boarding cutoffs independently.

Check both airport and terminal identifiers. An airport-wide map marker or shared city name cannot establish that two terminals connect on foot. For cross-airport moves, verify the ground route to the correct departure terminal and account for the relevant time of day. Where accessibility assistance is needed, verify its coverage across the whole transfer rather than assuming an airline's assistance continues onto public transport.

## Choose and record

List the steps in order from arrival gate to onward gate, including any baggage and queue stages. Keep published travel times distinct from estimated waits and processing. Reject a route whose required access permission is unresolved or whose chain misses a cutoff. If two routes exist, retain the eligible route even when an ineligible airside shortcut looks faster.

Use `planning.readiness[]` for terminal identity, access eligibility, and baggage handling checks. Reserve `planning.transport_edges[]` for map-supported landside legs with actual coordinate endpoints, a supported car/bus/walk map mode, and the required map action link. For an internal airside corridor or shuttle that cannot truthfully meet that contract, use a timed `note` event with `time` and `end_time` to reserve the transfer interval, and put the ordered internal steps and operator instructions in its `details` and `tips`. Link its access checks through readiness summaries and source references. Do not create an unbound `transport` event or fabricate map coordinates, a mode, or a map link. Add a `planning.booking_tasks[]` item only if a transfer or assistance arrangement must be secured. `event.details` should preserve the step order and cutoffs; `event.tips` should identify the action if the arrival terminal changes. Use the [existing transport contract](../itinerary-schema.md).

## Synthetic worked scenario

Arrival is 09:00. The eligible path needs an estimated 15 minutes walking, 35 for entry processing, 20 for bags, 25 for the terminal shuttle, and 30 for security and gate access: 125 minutes, reaching the onward gate at 11:05. Its cutoff is 11:10, leaving five minutes against the traveler's 20-minute contingency requirement. A fast airside corridor excludes this baggage path, so it cannot repair the calculation. Choose a later connection and verify its applicable cutoffs.
