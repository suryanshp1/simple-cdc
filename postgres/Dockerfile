FROM postgres:16

# Install wal2json logical decoding output plugin
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-wal2json \
    && rm -rf /var/lib/apt/lists/*
