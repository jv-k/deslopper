Follow-up from the review of the PR for #60, which added ten tells to the recommended preset.

## Finding

The new tells match only a straight apostrophe. "Here’s the thing:" with a curly apostrophe does not fire `false-suspense`. The same gap holds for every new pattern that contains `'`. <!-- deslop-lint-disable-line -->

## Why it was deferred

The regexes in #60 have the same gap. A curly apostrophe already fails the run through the error-tier `curly-quote` tell, so the writer fixes the quote before these tells matter.

## What to do

Replace `'` with `['’]` in the new patterns, so a tell still names the slop when `curly-quote` is disabled. Add a fixture case with a curly apostrophe. <!-- deslop-lint-disable-line -->
