FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vbpl_v3 vbpl_v3
# Configuration comes from --env-file; logs and model caches go to the mounted /app/work.
ENV V3_WORKDIR=/app/work
ENTRYPOINT ["python", "-m", "vbpl_v3"]
