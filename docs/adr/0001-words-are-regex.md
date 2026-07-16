# A tell's `words` are regex fragments, not literal words

A tell matches with either a `pattern` (a regex) or a `words` list. Despite the name, a
`words` entry is a regex fragment, not a literal string: the fragments are joined into one
alternation wrapped in word boundaries, `\b(?:a|b|c)\b`, and compiled as-is. The
`recommended` preset relies on this. `filler-verb` carries `utili[sz]es?` and
`(?-i:delve)s?(?=\s+(?:into|deeper))`, which only work because the entries reach `re.compile`
untouched.

We picked this over treating `words` as literals that get `re.escape`d. Literals would read
truer to the name, but they would strip the preset of the character classes, optional
suffixes, and lookaheads it already depends on, and those tells would then need rewriting as
`pattern` regexes. Keeping `words` as regex is the smaller, backward-compatible choice.

The cost is that the name misleads. Someone adding `c++` or `node.js` to a `words` list gets
a quantifier or an any-char, not the literal, with no error. That is a documentation problem,
not a reason to change the contract: [CONTRIBUTING.md](../../CONTRIBUTING.md) and the glossary
entry in [CONTEXT.md](../../CONTEXT.md) name the entries as regex. Do not "fix" the preset by
escaping its `words`.
