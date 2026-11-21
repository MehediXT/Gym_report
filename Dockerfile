# IronPulse Fitness — desktop GUI app image
# The GUI is shown on the host's X11 display (see docker-compose.yml / docker-run.sh).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Tk runtime + X11 client libraries + fonts for the CustomTkinter GUI
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libtk8.6 libx11-6 libxft2 libxss1 \
        fonts-inter fonts-dejavu-core fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user whose UID/GID match the host user (X11 socket access)
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} app && useradd -m -u ${APP_UID} -g ${APP_GID} app

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
USER app

CMD ["python", "main.py"]
