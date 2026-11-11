FROM python:3.13-slim

ARG TARGETARCH
ARG QUARTO_VERSION=1.10.19

RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) quarto_arch=amd64; quarto_sha256=7f0c4769e7f0e55f50d922f44b18db5118fb388d2b8fd27291fe1f8beafb43eb ;; \
      arm64) quarto_arch=arm64; quarto_sha256=35bb613052da98bef92ec3b7de77c3405a8e546363c7d2aa3abe15a39efa5045 ;; \
      *) echo "Unsupported Quarto architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl fontconfig fonts-liberation; \
    curl -fsSL "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-${quarto_arch}.deb" -o /tmp/quarto.deb; \
    echo "${quarto_sha256}  /tmp/quarto.deb" | sha256sum -c -; \
    apt-get install -y --no-install-recommends /tmp/quarto.deb; \
    quarto --version; \
    rm -f /tmp/quarto.deb; \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ASSISTENTE_V2_DATA_DIR=/data \
    ASSISTENTE_V2_DATABASE=/data/assistente_v2.sqlite3 \
    QUARTO_BINARY=quarto

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --system --create-home --home-dir /home/assistente --shell /usr/sbin/nologin assistente \
    && mkdir -p /data \
    && chown -R assistente:assistente /app /data
USER assistente
COPY --chown=assistente:assistente app app
COPY --chown=assistente:assistente templates templates
COPY --chown=assistente:assistente static static
COPY --chown=assistente:assistente _extensions _extensions
COPY --chown=assistente:assistente wsgi.py .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "120", "wsgi:app"]
