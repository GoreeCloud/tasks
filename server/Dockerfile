FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GOREECLOUD_TASKS_DATABASE=/data/tasks.sqlite3
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY goreecloud_tasks /app/goreecloud_tasks
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home --shell /usr/sbin/nologin tasks && mkdir -p /data && chown tasks:tasks /data
USER tasks
EXPOSE 8000
CMD ["uvicorn", "goreecloud_tasks.app:app", "--host", "0.0.0.0", "--port", "8000"]
