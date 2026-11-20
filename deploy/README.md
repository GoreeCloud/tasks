# Local-first deployment example

compose.yaml starts only the API and binds the host to loopback 127.0.0.1:8000, drops capabilities, restricts root FS and uses persistent /data. It does NOT expose a public web UI, install TLS, enable rate limiting, identity, alerts, backups, recovery checks or production monitoring.

    export GOREECLOUD_TASKS_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    docker compose up --build -d

Do not run in production unmodified. For remote use, a trusted HTTPS proxy must serve web/dist and route /api to the backend with body limits, network controls and rate limiting. Prefer an installed supported GoreeCloud Containers platform after independent workload acceptance. Protect the token and test a consistent SQLite online backup/restore (WAL requires care). Never commit secrets to Docker Compose files.
