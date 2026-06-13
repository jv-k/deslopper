---
title: front matter with an em dash — should be skipped
note: section § sign here is skipped too
---

# Heading with a semicolon; should flag

Prose with an em dash — and a section sign §.

Entities: &mdash; and &#8212; and &#x2014; and &sect; and &#167; and &#xA7;.

Two em dashes — on — one line.

- **Bold lead** then prose after the label should flag
- **Term:** definition list is exempt
- **Whole bold item**
1. **Numbered bold lead** then trailing prose flags

This leverages and enables and surfaces three filler verbs.

A seamless, robust, powerful set of marketing adjectives.

In today's world we open with throat-clearing.

Furthermore this is very really quite significantly intense.

This is not just fast but also clean padding.

Emoji line 🚀 with a checkmark ✅ and a star ⭐.

Inline `code with — em dash and ; semicolon` is masked.

Inline `&mdash;` entity inside code is masked too.

```text
fenced block with — em dash and ; semicolon and leverages, all skipped
```

This em dash — flags. <!-- deslop-lint-disable-line -->

<!-- deslop-lint-disable -->
This whole block — has a § and leverages but is disabled.
<!-- deslop-lint-enable -->

Back on — after enable, flags again.
