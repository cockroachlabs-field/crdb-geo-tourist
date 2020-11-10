FROM python:3.8-slim-buster
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get --yes --no-install-recommends install python3-dev build-essential cmake curl && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir -r requirements.txt && rm -rf ~/.cache/pip
EXPOSE 18080
ENTRYPOINT [ "python", "./map_app.py" ]

