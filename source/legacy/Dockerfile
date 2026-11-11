FROM hugomods/hugo:node-0.165.0 AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN hugo --minify

FROM python:3.13-alpine
RUN addgroup -S -g 10001 app \
    && adduser -S -D -H -u 10001 -G app app \
    && mkdir -p /var/lib/assistente-academico /usr/share/nginx/html \
    && chown -R app:app /var/lib/assistente-academico
WORKDIR /app
COPY --from=build --chown=app:app /src/public /usr/share/nginx/html
COPY --chown=app:app server.py /app/server.py
ENV ASSISTENTE_DATA_DIR=/var/lib/assistente-academico \
    ASSISTENTE_PUBLIC_DIR=/usr/share/nginx/html \
    ASSISTENTE_BIND=0.0.0.0 \
    ASSISTENTE_PORT=8080 \
    ASSISTENTE_COOKIE_SECURE=1
USER 10001:10001
EXPOSE 8080
CMD ["python3", "/app/server.py"]
