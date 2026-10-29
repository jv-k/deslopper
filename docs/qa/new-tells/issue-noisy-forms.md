Follow-up from the review of the PR for #60, which added ten tells to the recommended preset.

## Finding

The reviewer found forms that may flag honest prose:

- `hidden-truth` matches "the hard costs of hosting". <!-- deslop-lint-disable-line -->
- `mic-drop` flags a bare "It works." line through its `^\s*(?:it|this|that) (?:matters|works|...)\.\s*$` branch.
- `negation-pivot` matches "This is not a drill, this is a test." <!-- deslop-lint-disable-line -->

## Why it was deferred

Issue #60 set these regexes and said to move a noisy form to `aggressive` if it proves noisy. The repo's own lint has no hits, so there was no evidence to decide on.

## What to do

Run each form over a corpus of human technical prose, such as the Django docs. Where a form flags honest prose, narrow it or move it to the `aggressive` preset.
