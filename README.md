# SKALE Transaction Manager

[![Discord](https://img.shields.io/discord/534485763354787851.svg)](https://discord.gg/vvUtWJB)

Microservice used to manage sending concurrent transactions to the Ethereum network

## API

### sign_and_send

Takes transaction hash, signs and sends it, returns transaction hash.

-   URL: `/sign-and-send`
-   Method: `POST`

**Request body**:

```json
{
    "transaction_dict": "TRANSACTION_DICT_STRING",
}
```

**Success Response**:

```json
{
    "errors": null,
    "data": {
        "transaction_hash": "0x..."
    }
}
```

**Error response**:

```json
{
    "error": "Error message",
    "data": null
}
```

### sign

Takes transaction hash, signs it, returns signed transaction.

-   URL: `/sign`
-   Method: `POST`

**Data Params**:

```json
{
    "data": {
        "transaction_dict": "TRANSACTION_DICT_STRING",
    }
}
```

**Success Response**:

```json
{
    "errors": null,
    "data": {
        "transaction_hash": "0x..."
    }
}
```

**Error response**:

```json
{
    "error": "Error message",
    "data": null
}
```

### address

Returns wallet address.

-   URL: `/address`
-   Method: `GET`

**URL Params**:

None.

**Success Response**:

```json
{
    "errors": null,
    "data": {
        "address": "0x..."
    }
}
```

**Error response**:

```json
{
    "error": "Error message",
    "data": null
}
```

### public_key

Returns wallet public key.

-   URL: `/public-key`
-   Method: `GET`

**URL Params**:

None.

**Success Response**:

```json
{
    "errors": null,
    "data": {
        "public_key": "0x..."
    }
}
```

**Error response**:

```json
{
    "error": "Error message",
    "data": null
}
```

## Development

### Run development server

Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run server:

```bash
export $(grep -v '^#' .env | xargs) && python server.py
```

Build and run test container

```bash
docker build -t test-tm .
docker run  --env-file .env-docker -v ~/.skale:/skale_vol -v ~/.skale/node_data:/skale_node_data test-tm
```

Run `transaction-manager` container locally

```bash
VERSION=0.0.1-develop.0 && docker run -p 3008:3008 --env-file .env-docker -v ~/.skale:/skale_vol -v ~/.skale/node_data:/skale_node_data skalelabshub/transaction-manager:$VERSION
```

## License

[![License](https://img.shields.io/github/license/skalenetwork/transaction-manager.svg)](LICENSE)

All contributions are made under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.en.html). See [LICENSE](LICENSE).

All transaction-manager code Copyright (C) SKALE Labs and contributors.
