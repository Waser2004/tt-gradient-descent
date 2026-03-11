FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends make iverilog \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/test

COPY test/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["make", "-B"]
