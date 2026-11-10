FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-nanum && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
RUN pip install --no-deps . && useradd -m agent && mkdir -p /app/var/files && chown -R agent:agent /app
USER agent
CMD ["uvicorn","meeting_agent.main:create_app","--factory","--host","0.0.0.0","--port","8000","--no-access-log"]

