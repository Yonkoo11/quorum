# The QUORUM buy bot as a tiny always-on worker. Token and chat come from the host's
# environment (its secret store), never baked into the image.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY buybot.py .
RUN mkdir -p /data

# BUYBOT_TG_TOKEN, BUYBOT_TG_CHAT (and optional BUYBOT_MIN_USD, QUORUM_RPC) are set as host secrets.
# The state file lives on the container's own disk; a restart re-reads recent blocks and dedupes.
ENV BUYBOT_STATE=/data/buybot-state.json
CMD ["python", "-u", "buybot.py"]
