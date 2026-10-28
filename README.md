# SKALE Transaction Manager

[![Discord](https://img.shields.io/discord/534485763354787851.svg)](https://discord.gg/vvUtWJB)

Microservice used to manage sending concurrent transactions to the Ethereum network

## Usage

Clients submit transactions through Redis with `RedisWalletAdapter` from skale.py.

## Development

Install dependencies:

```bash
uv sync --all-extras
```

Lint and type check:

```bash
uv run ruff check
uv run mypy transaction_manager
```

Run tests (requires `ETH_PRIVATE_KEY`, `ENDPOINT` and Docker):

```bash
./scripts/run-test-containers.sh
./scripts/run-tests.sh
./scripts/run-docker-tests.sh
```

## License

[![License](https://img.shields.io/github/license/skalenetwork/transaction-manager.svg)](LICENSE)

All contributions are made under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.en.html). See [LICENSE](LICENSE).

All transaction-manager code Copyright (C) SKALE Labs and contributors.
