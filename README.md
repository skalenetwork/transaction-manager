# SKALE Transactions Manager

Microservice used to manage transactions sending from the SKALE Node to the Ethereum network.

## Delevopment

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
