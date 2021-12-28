FROM python:3.8-buster

RUN apt-get update && apt-get install build-essential python-dev --yes

RUN mkdir app
WORKDIR /app

COPY transaction_manager transaction_manager

RUN apt install libssl-dev swig
RUN git config --global http.postBuffer 2147483648

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONPATH="/app"
CMD ["python3", "-m", "transaction_manager.main"]
