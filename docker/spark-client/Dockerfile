FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyspark==3.5.3 pandas matplotlib pytest
ENV HADOOP_CONF_DIR=/opt/conf SPARK_CONF_DIR=/opt/conf PYTHONPATH=/app
COPY conf/ /opt/conf/
WORKDIR /app
