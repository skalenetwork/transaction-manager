FROM python:3.11-bookworm

RUN apt update && apt install build-essential libssl-dev swig --yes

RUN mkdir app
WORKDIR /app

COPY transaction_manager transaction_manager

RUN git config --global http.postBuffer 2147483648

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONPATH="/app"
CMD ["python3", "-m", "transaction_manager.main"]
