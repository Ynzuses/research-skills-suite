# Session Lifecycle

## Startup Protocol

The goal of startup is verified orientation, not exhaustive reading.

1. **Locate scope.** Confirm the actual working directory and discover the most specific applicable rules.
2. **Read the entry layer.** Read workspace rules and the long-term memory index completely.
3. **Resolve active work.** Identify the project, phase, or workstream that owns the request.
4. **Read current status.** Capture objective, last verified state, blockers, and recorded first action.
5. **Route by task.** Open only the stable design, asset index, topic memory, dependency graph, or audit record needed.
6. **Verify before mutation.** Check consequential locations and state against physical artifacts or primary systems.
7. **Start or correct.** Follow the recorded next action if still valid; otherwise record why it changed.

If the entry layer and physical workspace disagree, inspect the workspace first and repair the route before continuing.

## In-Session Capture

Update the appropriate layer when one of these events occurs:

| Event | Update |
| --- | --- |
| policy, permission, or privacy boundary changes | rules |
| durable cross-project lesson or route changes | long-term memory index |
| progress, blocker, or next action changes | current status |
| scope, definition, input contract, or approved method changes | stable design plus history |
| authoritative artifact is created, replaced, moved, or retired | asset index plus affected links |
| durable bounded-domain lesson emerges | topic memory and parent route |
| dependency or execution order changes | DAG or workflow map |
| consequential decision closes | history with evidence and supersession |
| artifact is submitted or formally circulated | freeze its identity in status and asset index; route later feedback to a new revision |
| detailed investigation closes | audit archive, then link from the owning record |

Maintain a small event queue during the task. Coalesce repeated events affecting the same authority, verify the final artifact, and update each affected layer once near closure. Do not write memory for every command. Preserve durable meaning: what became true, why it matters, where the evidence is, and what should happen next.

Do not touch memory files when no durable event occurred. A read-only answer, an unchanged audit, or a transient failed command is not by itself a memory event.

## Closure Protocol

Close only after inspecting the outputs that the handoff will claim.

1. List created, changed, retired, and merely inspected artifacts.
2. Validate existence, content, hashes, render, or execution state in proportion to risk.
3. Resolve the queued durable events and update only their owning layers.
4. Update current status with a concrete first action that can be executed without reconstructing the session.
5. Record blockers with the condition that would clear each one.
6. Update stable design only for durable approved changes; distinguish provisional decisions.
7. Update asset routes and synchronization directions.
8. Append a dated history entry for consequential decisions and state what it supersedes.
9. Move closed detail out of the active context and leave a link to the audit record.
10. Re-run the startup route mentally or with a fresh reader: rules/index, status, task evidence.
11. After the status/index/audit-pointer edits are complete, rehash authoritative artifacts and re-run the hash-bound checks; do not leave the handoff pointing at an audit made before the final metadata edit.
12. If an artifact was submitted, mark the submitted hash as frozen and name the next revision identity or feedback trigger; do not leave the next session free to overwrite the baseline silently.

The final handoff should state outcome, authority, verification, unresolved risk, and next action. It should not require the next session to read the chat transcript.

## Handoff Record

A robust handoff contains:

- **Outcome:** what is now complete or materially changed;
- **Authority:** which artifact now governs each changed fact;
- **Evidence:** how the state was verified;
- **Open items:** blockers, provisional decisions, and unverified assumptions;
- **First action:** one concrete next step, including its input and expected output;
- **Routes:** links or stable IDs needed to continue.

Use timestamps with time zone when order matters. Avoid “continue the analysis” or “check results” as next actions; name the object and the acceptance condition.

## Compaction and Recovery

When chat context is compressed or lost, do not reconstruct from memory alone. Re-enter through the same startup protocol. Trust persisted authorities over conversational recollection, then verify artifacts.

If work stopped unexpectedly:

1. inspect the current status and latest history entry;
2. verify recent artifacts and partial outputs;
3. distinguish complete, incomplete, stale, and true zero-result states;
4. record the recovered state and safest rerun or continuation point;
5. avoid deleting ambiguous artifacts until ownership and recoverability are known.

## Staleness Controls

- Put `last verified` on status and high-risk asset entries.
- Store the verifier or method, not only a date.
- Mark provisional claims and expiry conditions.
- Prefer event-driven updates over meaningless routine touches.
- When a status claim is wrong, repair it immediately and record the reason if consequential.
- Archive completed phases so they do not remain in the default startup path.

## Fresh-Session Test

Give a reader only the workspace entry point and a user-like task. The system passes if the reader can, without prior chat:

1. discover constraints;
2. identify the active scope;
3. find verified current state;
4. locate the right authority;
5. state the next action and major risk;
6. avoid loading unrelated topic memory.
