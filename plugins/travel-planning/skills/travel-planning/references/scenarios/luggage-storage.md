<!-- travel-guide: {"id":"luggage-storage","title":"Luggage storage on the departure critical path","category":"transport","when":"Use when stored luggage must be retrieved between sightseeing, checkout, and a time-bound departure.","tags":["left luggage","storage cutoff","行李寄存","取行李"]} -->

# Luggage storage on the departure critical path

## Activate when retrieval can change the day

Use this guide when a traveler will leave bags somewhere other than the next overnight location and must collect them before continuing. It adds little when bags remain in a confirmed room until departure and no retrieval detour or access cutoff exists.

Ask for bag count, approximate size category, retrieval date, and whether stairs or a long walk would make a storage location unsuitable. Do not request bag contents, lock codes, identity scans, or storage claim codes. If a provider has restrictions relevant to the traveler, let the traveler check those privately.

## Verify both access and retrieval

Verify the operator, exact entrance, staffed or locker access hours, size limits, capacity or reservation method, and retrieval conditions. Separate the venue's opening hours from the storage desk's hours. Confirm whether retrieval requires a ticketed or security-controlled area that the traveler can still enter after checkout or arrival.

Treat walk time to storage, retrieval time, and travel to the departure checkpoint as separate steps. Capacity listed on a website is not a reservation. If same-day availability cannot be secured, identify a second storage location that fits the same route before making the sightseeing schedule depend on it. A closed desk cannot be rescued by an otherwise open station.

## Choose and record

Work backward from the departure's applicable access or check-in deadline, adding the traveler's contingency buffer. The latest sightseeing finish must satisfy both that result and the storage retrieval cutoff. If those constraints conflict, shorten the visit, move storage closer to the departure point, or keep the bags with the traveler where permitted.

Use `planning.readiness[]` for size, access, and retrieval confirmation. Put a required storage reservation in `planning.booking_tasks[]`; do not represent an unreserved locker as booked. Include the retrieval detour in `planning.transport_edges[]` rather than hiding it in a tip. `event.details` should name the retrieval entrance and latest return time; `event.tips` should give the capacity-failure alternative. Apply the [readiness evidence fields](../trip-readiness.md) to the chosen location.

## Synthetic worked scenario

A train's required checkpoint time is 17:40. Storage-to-checkpoint walking takes 20 minutes; retrieval takes an estimated 15 minutes, with 15 minutes of contingency. The traveler must reach storage by 16:50. The selected desk instead closes at 16:30, so 16:50 is unusable. Move collection earlier or select a verified alternative desk open beyond 16:50; the original sightseeing finish cannot remain unchanged.
