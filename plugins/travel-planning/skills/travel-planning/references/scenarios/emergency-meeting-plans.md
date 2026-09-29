<!-- travel-guide: {"id":"emergency-meeting-plans","title":"Pre-Separation Meeting Plans","category":"readiness","when":"Use before a trip or planned separation to agree regrouping rules for possible communication loss; not during an active separation, emergency, or evacuation.","tags":["communication loss","meeting points","失联集合","应急会合","pre-trip","pre-separation","行前集合","分离预案"]} -->

# Pre-Separation Meeting Plans

## Activation and limits

Use this guide before travel or planned separation, while the party can still agree a regrouping procedure for possible communication failure. Do not use it to create new shared rules during an active separation or communication-loss incident, even when every traveler is independently mobile. It is not a search-and-rescue protocol or a reason to delay emergency assistance. Immediate danger, a missing dependent traveler, or an official evacuation requires the relevant local emergency or venue procedure, not a generic waiting rule.

## Minimum functional inputs

Collect anonymous party counts, who must remain accompanied, who can independently reach a meeting point, and which parts of the route could lose communication. Ask which private contact method the travelers will manage themselves, without collecting its account details or phone numbers. No identity documents, home addresses, or live tracking access are needed.

## Decision procedure

1. Select a precise primary meeting point for the affected area. Verify access hours, entry restrictions, recognizable signage, and whether everyone can reach it by an acceptable route. “At the station” is insufficient when exits are far apart or separated by ticket barriers.
2. Choose a distinct fallback for closure or loss of access, and specify the condition for using it. A fallback inside the same closed building does not resolve that failure. Check the route between points rather than assuming visibility means accessibility.
3. Agree what each capable subgroup does after communication loss, including destination local time and a traveler-chosen waiting or move-on rule. Avoid instructions that send groups searching along opposite routes. Do not instruct a dependent traveler to move independently.
4. Identify official public assistance channels and relevant venue procedures, verifying them for the jurisdiction and date. Keep private contact cards and emergency personal information under traveler control, separate from the exported itinerary.
5. Explain when the meeting plan stops applying: an unsafe location, evacuation direction, missing dependent traveler, or another urgent situation. Follow official assistance instructions then. Do not invent a universal delay before seeking help, and do not assume that data service or a staffed desk will remain available.

## Record and fallback

Store the operational meeting rule in `planning.readiness[]`, with official sources and unresolved checks. Use event `details` or `tips` for the relevant point and condition, and existing attraction entrance or exit fields where appropriate. A planned regrouping can be an ordinary `note` event; it must not imply the renderer provides live tracking or emergency communication. Follow [trip readiness](../trip-readiness.md) and the [itinerary schema](../itinerary-schema.md). Unverified access remains `to_recheck` with an actionable official HTTPS link.

## Synthetic decision example

Before entering a fictional museum complex, two independently mobile adult subgroups agree to use the publicly accessible south entrance if data is lost, with a checked plaza as the closure fallback. They rehearse the same rule while contact is available, rather than planning to search each other's galleries or negotiate a new meeting point after communication fails. If the venue directs evacuation elsewhere, its instruction overrides both meeting points; the plan does not promise that either remains usable.
