FROM python:3.7

RUN mkdir /usr/src/transaction-manager
WORKDIR /usr/src/transaction-manager

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH="/usr/src/transaction-manager"
CMD ["python", "server.py"]
