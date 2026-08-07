## Purpose

`async_rithmic` is a focused async Python client for the Rithmic API.

Contributions should preserve the codebase's defining qualities:

- direct async control flow;
- concrete protocol-facing code;
- clear ownership by plant;
- small public methods;
- explicit failure behavior;
- focused regression tests.

## General style

Favor simple, expressive code.

- Prefer the smallest correct solution.
- Keep the normal execution path easy to read from top to bottom.
- Use direct method calls and explicit state.
- Keep abstractions concrete and local.
- Extract helpers only when they make the main flow easier to follow.
- Avoid clever code when a short loop or condition is clearer.
- Match the style of the surrounding module.
- Keep diffs narrow and avoid unrelated cleanup.

Do not redesign nearby code unless it is necessary for the requested change.

## Comments and docstrings

Keep comments concise.

Comments should explain:

- protocol behavior;
- correctness invariants;
- non-obvious edge cases;
- why a seemingly simpler implementation is unsafe.

Do not:

- narrate obvious code;
- repeat the function name;
- write long implementation essays inside the source;
- preserve outdated comments after behavior changes.

Prefer expressive names and structure over explanatory comments.

Public docstrings should briefly describe behavior, important side effects, and notable failure cases. Private helpers usually do not need docstrings when their purpose is clear from the name.

## Repository ownership

- `async_rithmic/client.py` constructs plants and delegates their public methods.
- `async_rithmic/plants/base.py` owns behavior genuinely shared by all plants.
- `async_rithmic/plants/*.py` own endpoint-specific requests, responses, and state.
- `async_rithmic/helpers/` contains small reusable async mechanisms.
- `async_rithmic/objects.py` contains simple state and configuration dataclasses.
- `tests/` contains focused pytest tests.

Keep behavior in the narrowest appropriate owner. Do not move endpoint-specific logic into the client or base plant for convenience.

## Python style

- Use descriptive domain names.
- Prefer short functions with one clear responsibility.
- Add type annotations where they improve understanding.
- Preserve the existing public API unless a correctness fix requires a change.

## Async correctness

Async lifecycle behavior is part of the public contract.

- Never perform blocking I/O or use blocking sleeps in async code.
- Every long-lived task must have a clear owner and shutdown path.
- Preserve cancellation. Catch `asyncio.CancelledError` only for cleanup, then re-raise it.
- Do not leave callers blocked after an error.
- Request state must be finalized or removed on success, timeout, cancellation, provider error, and local processing error.
- When waiting on multiple tasks, cancel and clean up unfinished tasks.
- Callbacks and returned results should contain the same accepted records in the same order unless documented otherwise.
- Do not swallow exceptions. Broad catches are acceptable only for narrow cleanup or logging and should normally re-raise.

## Final checklist

- [ ] The normal execution path is easy to follow.
- [ ] The solution is no more complex than necessary.
- [ ] Comments are concise and useful.
- [ ] Async tasks and request state are cleaned up.
- [ ] Errors are explicit.
- [ ] Focused tests cover the change.
- [ ] The full test suite passes.
- [ ] The diff contains no unrelated changes.
