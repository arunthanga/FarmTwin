## Summary
<!-- What does this PR do? One paragraph. -->

## Type
- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `test` — tests only (no product code change)
- [ ] `docs` — documentation
- [ ] `refactor` — no behaviour change
- [ ] `ci` — CI/tooling change

## Scope
- [ ] `solver` (GGA, MOC, Richards, Surface)
- [ ] `fao56` (ET₀, crop water)
- [ ] `schema` (FTS survey format)
- [ ] `quality` (B6 QC gate)
- [ ] `iot` (edge, firmware)
- [ ] `studio` / `runtime` / `cloud`

## White-paper reference (if solver change)
<!-- Required for any change to a physics module -->

## Checklist
- [ ] Ruff passes (`ruff check engine/ && ruff format --check engine/`)
- [ ] Unit tests pass (`pytest -m "unit and not tdd"`)
- [ ] TDD stubs added for any new unimplemented feature (`pytest -m tdd`)
- [ ] Physical constants are named (no bare literals in solver loops)
- [ ] All equations cite reference (author, year, eq. number) in docstring
- [ ] `CHANGELOG.md` updated
- [ ] `requirements.md` updated if architecture changes
