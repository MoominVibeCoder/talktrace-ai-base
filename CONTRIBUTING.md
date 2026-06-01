# Contributing to TalkTrace AI base

Thank you for considering a contribution.

## How to contribute

- **Bug reports**: open an issue with the OS, Python version, provider, and a minimal reproduction (transcript snippet + codebook excerpt if relevant).
- **Feature requests**: open an issue to discuss before opening a PR. Some larger experimental features intentionally live in a private internal research version; we want to align scope before code is written.
- **Pull requests**: fork, branch from `master`, keep diffs focused. One topic per PR.

## Development setup

```bash
git clone https://github.com/MoominVibeCoder/talktrace-ai-base.git
cd talktrace-ai-base
./start.sh           # Linux/macOS
start.bat            # Windows
```

`start.sh` / `start.bat` provisions a virtual environment and installs dependencies on first run. For active development with hot-reload, use `dev.sh` / `dev.bat`.

## Coding conventions

- Python 3.12+ (development target: 3.13).
- Match the existing style in surrounding files. Comments should explain *why*, not *what*.
- Add tests under `tests/` when adding non-trivial logic.

## License of contributions

By submitting a contribution you agree it is licensed under the GNU Affero General Public License, Version 3.0 (AGPL-3.0) — the same license as the project (see [LICENSE](LICENSE)). AGPL-3.0 is a strong copyleft license with a patent-grant clause and a network-use provision, ensuring that downstream users (including users of any hosted service built on this code) retain access to the corresponding source.

## Code of conduct

By participating you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please do not file security issues as public GitHub issues. See [SECURITY.md](SECURITY.md) for the responsible-disclosure address.
