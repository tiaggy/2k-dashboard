# Attendance web dashboard. Reads/writes the same Notion workspace as the
# 2k-grouper bot (github.com/tiaggy/2k-grouper) via its own .env — the two
# projects only ever communicate through Notion, never directly. This DOES
# publish a port (it's a web page, not a long-poller) — see README.md for how
# that's exposed safely (bound to loopback by default; the Docker + UFW
# gotcha applies here same as any container publishing a port).
FROM python:3.13-slim-bookworm

# tzdata: "this week" / week boundaries are computed in local time, so the
# container must know its timezone (set TZ in the environment).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATE_DIR=/data

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py notion.py notion_http.py notionapprovals.py attendance.py ./
COPY dashboard/ ./dashboard/

RUN mkdir -p /data && useradd -m -u 10002 dashuser && chown -R dashuser /app /data
USER dashuser
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "dashboard.server:app", "--host", "0.0.0.0", "--port", "8000"]
