<!-- travel-guide: {"id":"medication-logistics","title":"Medication Carrying and Storage Logistics","category":"readiness","when":"Travel depends on arranging medication carriage, storage, or access across the planned route.","tags":["medication logistics","storage","携药安排","药品储存"]} -->

# Medication Carrying and Storage Logistics

## Activation and limits

Use this guide for the logistical dependencies of an existing traveler-managed medication plan. It does not recommend medication, alter doses or timing, interpret symptoms, or determine legal admissibility. The traveler obtains individual advice from a clinician or pharmacist and applies relevant government and carrier requirements privately.

## Minimum functional inputs

Collect travel dates and jurisdictions, whether special storage or power is required, whether items must remain accessible during transit, and whether an operator arrangement needs confirmation. A functional statement such as “storage conditions require verification” is sufficient for the shared plan. Do not request prescriptions, medicine inventories, diagnoses, identity documents, or document numbers. Any product-specific eligibility questions can remain in the traveler's private consultation.

## Decision procedure

1. Trace the complete possession and storage chain: departure, screening, each flight or train, layovers, baggage handling, ground transfers, and accommodation. Identify periods when the item or necessary power would be inaccessible.
2. Direct the traveler to current official guidance for each relevant jurisdiction and carrier, including transit where applicable. Distinguish carriage permission, security screening, import restrictions, documentation, and equipment rules; evidence for one does not resolve the others.
3. Obtain storage conditions from authoritative product information or the traveler's professional advice. Verify whether the proposed facility can meet those conditions throughout the relevant period. A room listing that says “minibar” does not establish a suitable storage arrangement.
4. Check advance-request procedures, confirmation scope, and handover or retrieval times for operator-provided arrangements. Represent pending requests honestly. Do not assume that onboard refrigeration, charging, replacement supplies, or local dispensing is available.
5. Ask the traveler to resolve an interruption plan with the appropriate professional or operator. If a critical dependency remains unresolved, leave the dependent leg unconfirmed and consider a route or property change through the existing route-confirmation workflow.

## Record and fallback

Use `planning.readiness[]` for nonclinical dependencies, public official `source_ids`, `checked_at`, and unresolved questions. Mark a published rule as checked only within its evidenced scope; do not claim that the traveler's private eligibility is verified. Use `planning.booking_tasks[]` for required operator arrangements, and event `details` or `tips` for a neutral reminder to complete the private check. Keep private documents and product-specific correspondence out of exported artifacts. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md).

## Synthetic decision example

A fictional traveler needs an independently specified storage condition during an overnight stop. Hotel A advertises a minibar but cannot confirm the relevant conditions. Hotel B describes a suitable arrangement with a retrieval procedure that fits departure. Treat A as unresolved and make B conditional on the traveler's acceptance and confirmed arrangement; do not change the medication plan to fit either hotel.
