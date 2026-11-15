FROM python:3.12.10-slim-bookworm

RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir discord.py
WORKDIR /app
COPY bot.py .
CMD ["python", "-u", "bot.py"]
