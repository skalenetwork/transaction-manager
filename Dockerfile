FROM python:3.7

RUN apt-get update && apt-get install build-essential python-dev --yes
RUN mkdir app
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH="/app"
CMD ["uwsgi", "--ini", "uwsgi.ini"]
