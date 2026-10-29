Adds `docs/research/slop-tells-survey.md`, a survey of slop tells that other detectors and articles list and that the `recommended` and `aggressive` presets miss. Each candidate has a draft regex, its hit count over the Django 3.2 docs (human technical prose written before chatbots), a suggested tier and its sources.

#60 (PR #64) and #61 build the first part of it. The spec for the remaining candidates links here, so the build agent reads the draft regexes from the repo.

Quoted examples that contain tells sit in exempt regions, so the file stays clean after #64 adds those tells.

Docs only. `deslopper lint` and the pre-commit hooks passed on the commit.

https://claude.ai/code/session_01H9P8oHumognjMPpA8veVsi
