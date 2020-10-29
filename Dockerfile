FROM python:3.8-buster

RUN apt-get update && apt-get install build-essential --yes
RUN mkdir app
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH="/app"
CMD ["python", "main.py"]
