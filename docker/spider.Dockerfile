FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libxml2-dev libxslt1-dev zlib1g-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY scrapy.cfg .
COPY src/ src/

# 通过环境变量指定爬虫名，默认 example_spider
ENV SPIDER_NAME=example_spider
CMD ["sh", "-c", "scrapy crawl $SPIDER_NAME"]
