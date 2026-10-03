# Sensitive-data boundary

This plugin researches ordinary travel and produces itineraries. It does not implement confidential-message delivery, recipient authentication, end-to-end payload encryption, or a key-management protocol. Do not describe it as suitable for classified information, certified, or guaranteed to keep all information private.

## Decide before using tools

Apply this decision before provider preflight, preliminary destination research, direct MCP/CLI calls, browser searches, delegating research, creating a workspace, archiving input, or rendering a delivery artifact.

| Input or requirement | Action |
| --- | --- |
| Ordinary travel planning with no restricted information | Follow the existing workflow and authorization rules. Send only the travel fields needed by the selected source. Avoid names, private contact details, booking identifiers, credentials, and unrelated background. |
| Confidential, restricted, classified, or ambiguous claims such as “top secret” | Pause processing of the affected material. Ask only about its classification, intended recipient type, and permitted environment or channel. Do not request the payload itself. Use synthetic examples or public information for independent work. |
| A requirement that the information never reach an external service | Do not run the ordinary online research workflow on that information. An existing API key or prior route confirmation does not establish that an external service is an approved recipient. |
| Credentials, account sessions, identity documents, or private personal identifiers offered as research input | Do not copy them into queries, task prompts, workspace files, logs, tests, issues, PRs, JSON, or HTML. Request a minimal description of the travel constraint instead. Credential setup remains in the existing user-controlled local configuration flow. |
| Public venue contacts or public emergency numbers | Treat them as public travel facts when relevant; do not confuse them with a traveler's private contact information. |

Do not ask for a sample secret to determine the classification. If material is already identified as restricted, avoid further opening, quoting, copying, delegating, or transmitting it through this plugin. Explain the boundary without reproducing the material. Do not claim that earlier messages, tool calls, files, logs, backups, or service records have been erased.

Clarify ambiguous sensitivity once at the relevant boundary. Ordinary travel queries do not need repeated permission prompts solely because they contain a date or public destination. Existing permissions for routine work remain applicable within their original data scope.

## Existing data paths

These are current implementation boundaries, not additional protections:

| Path | What the implementation does | Consequence |
| --- | --- | --- |
| Host and model | The host supplies the conversation and tool context before or while executing a Skill. | Skill text cannot retroactively control host processing or retention. Host approval and configuration require separate evidence. |
| Provider queries | Python launchers, direct APIs, and MCP tools send travel parameters to the selected services. | Read-only access can still disclose query contents. HTTPS protects transport to a service; the service receives the query. |
| Provider processes | Launchers pass a minimal runtime environment, explicitly configured extra variables, and the selected provider's credentials, then run third-party code as the invoking user. | Environment minimization is not filesystem, process, or network isolation. |
| Workspace and export | Research helpers persist JSON and documents; the renderer writes readable HTML. | Possession of these files provides their contents. File permissions and hashes are not recipient encryption or authentication. |
| Xiaohongshu state | The local runtime maintains cookies and logs. Research commands also keep query metadata and temporary note tokens in a user-global cache by default. | A per-trip research workspace does not imply that all provider state is per-trip or automatically expires. |
| HTML resources | Images can use external HTTPS URLs. AMap frames contain route names, coordinates, and waypoints and load as the page is viewed. | A single HTML file with inline JavaScript/CSS is not necessarily offline or network-silent. Referrer restrictions do not prevent the request itself. |
| Preflight | `--skip-upstream` skips provider smoke queries but can still initialize MCP processes and resolve npm packages. | It is not an enforced offline mode. Do not run it on the assumption that it makes no network requests. |
| Packaging | Git selects tracked and nonignored untracked files. The local packager rejects known private runtime paths and unsafe symlink targets; CI also checks package contents. | Ignore rules do not remove already tracked files, and path guards are not a complete content-based secret detector. Review actual archive contents before distribution. |

The optional `--private-offline` renderer profile removes scripts and embedded media and adds a restrictive Content Security Policy; intentional external links remain. Owner-only POSIX artifact permissions reduce local exposure. Neither control encrypts the content or authenticates recipients. The default interactive HTML and online research workflow retain their external-service boundaries.

Implementation anchors: [provider environment](../../scripts/runtime_env.py), [MCP declarations](../../.mcp.json), [research sources](../../skills/travel-planning/scripts/research_sources.py), [workspace](../../skills/travel-planning/scripts/research_workspace.py), [renderer](../../skills/travel-planning/scripts/render_itinerary.py), and [Xiaohongshu runtime](../../skills/xiaohongshu/scripts/setup.py).

## Requests for confidential delivery

Keep restricted payloads outside this plugin and its research/model/provider paths. For an organization with an approved communication channel, direct the user to its responsible security owner and approved process; do not substitute an arbitrary consumer service or send anything on the user's behalf.

A separate implementation requires a defined classification and threat model, authenticated sender and recipient identities, independently verified keys, an established reviewed encryption protocol, key rotation/recovery/revocation rules, controlled endpoints, enforceable egress restrictions, retention and backup rules, and independent verification. Formally classified use also requires the applicable authority's deployment approval. These requirements are not satisfied merely by adding a password, encrypting an already generated HTML file, passing CI, or using a cryptographic library.

Use synthetic data to test wrong-recipient handling, tampering, replay, key loss, authorization failure, unintended network requests, and sensitive diagnostic output before considering real confidential material. Never imply that a successful test provides formal accreditation or universal privacy assurance.

The instructions on this page are a host-behavior boundary. They add no cryptographic transport, no network firewall, and no runtime secret detector. A host that bypasses the Skills can still invoke registered tools directly. Enforce a stricter deployment boundary outside the Skill before accepting restricted payloads.
