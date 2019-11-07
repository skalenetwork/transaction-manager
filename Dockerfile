FROM python:3.7

RUN mkdir /usr/src/transactions-manager
WORKDIR /usr/src/transactions-manager

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH="/usr/src/transactions-manager"
CMD ["python", "server.py"]
