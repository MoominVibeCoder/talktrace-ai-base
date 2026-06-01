<!-- Thanks for sending a pull request. The checklist below is short on purpose — please tick what applies. -->

## Summary

<!-- One or two sentences: what does this change and why? -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (existing behaviour intentionally altered)
- [ ] Documentation / tooling only

## Linked issues

<!-- Closes #123, refs #456 — or "none" if this is unsolicited. -->

## Test plan

<!-- How did you check this works? Manual click-through, smoke test, fixture run? -->

- [ ] App still launches via `start.bat` / `start.sh` after the change.
- [ ] Imports resolve in a fresh `.venv` (`pip install -r requirements.txt && python -c "from talktrace_ai import app"`).
- [ ] If UI changed: tested in both light and dark themes.
- [ ] If localization changed: both DE and EN strings updated.

## License

By submitting this pull request you confirm that your contribution is licensed under the [GNU Affero General Public License v3.0](LICENSE) — the same license as the project — and that you have read and agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
