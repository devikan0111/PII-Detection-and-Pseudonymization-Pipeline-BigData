FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PIP_DEFAULT_TIMEOUT=1000 PIP_RETRIES=10
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir pyspark==3.5.1
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_lg
COPY . .
ENV PYTHONPATH=/app/src
CMD ["bash", "scripts/run_all.sh"]