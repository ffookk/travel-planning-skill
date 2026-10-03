<!-- travel-guide: {"id":"dietary-cross-contact","title":"Dietary Requirements and Cross-Contact Questions","category":"readiness","when":"A meal choice depends on ingredient exclusions or preparation practices that a menu alone cannot establish.","tags":["dietary requirements","cross-contact","饮食限制","交叉接触"]} -->

# Dietary Requirements and Cross-Contact Questions

## Activation and limits

Use this guide when ingredient exclusions, shared preparation, or service practices determine whether a restaurant is a usable candidate. It does not assess medical risk, establish a safe exposure level, or certify a restaurant. Clinical advice and the traveler's own requirements remain external to the planning decision.

## Minimum functional inputs

Ask which ingredients or preparation practices must be avoided, whether shared equipment is unacceptable, and which fallback arrangements the traveler already accepts. No diagnosis or reaction history is needed. Record only the functional constraints necessary for the meal plan, and agree what may appear in an itinerary that could be shared.

## Decision procedure

1. Separate menu evidence from preparation evidence. A dish description can support an ingredient question; it cannot establish handling, substitutes, sauces, shared fryers, or equipment cleaning.
2. For each candidate, identify the operator's current dietary information and an official contact route. Prepare concrete questions about the requested dish, service date, and relevant preparation practices. A traveler can obtain clarification; the guide does not authorize the agent to send messages or make reservations.
3. Record what the operator actually establishes and what remains unanswered. Do not upgrade a menu icon, third-party review, or “we usually can” response into confirmation of the required process. Keep source dates and any service-specific limitations.
4. Rank only candidates that meet the traveler's stated requirements with adequate evidence. Independently assess the fallback: a nearby restaurant with a similar menu does not inherit the main candidate's evidence.
5. Reconfirm when the dish, service, or preparation arrangement changes. If essential answers remain unavailable, keep the candidate unresolved and use a traveler-approved alternative with its own evidence. Do not recommend testing tolerance or silently relaxing a requirement.

## Record and fallback

Follow [restaurant research](../restaurant-research.md): restaurant identity, dynamic facts, and route evaluation retain their existing records. Put the functional requirement, scope of operator evidence, and outstanding questions in `planning.readiness[]`, linked to the candidate through an unambiguous summary and `source_ids`. Use `to_recheck` and an official HTTPS action link for an unanswered essential question. Keep actual candidate selection and switching in `planning.meal_options[]`, including `fallback_candidate_ids[]` and `fallback_rule`; do not create a free-text substitute meal or invent an allergy-status field. Event `tips` may prompt traveler confirmation at arrival. One qualifying candidate does not complete a normal meal: continue researching an independently qualifying fallback. Use the existing constrained-candidate exception only when its evidence, reason, and emergency fallback satisfy the restaurant contract. See [trip readiness](../trip-readiness.md).

## Synthetic decision example

Restaurant A's fictional menu excludes an ingredient from one dish, but its operator cannot establish the requested shared-equipment restriction. Restaurant B provides current, service-specific information that meets the traveler's stated requirement. Select B after checking its route and meal window; leave A unresolved. A generic menu icon does not make A an evidenced fallback.
