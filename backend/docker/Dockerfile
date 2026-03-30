FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin sandbox

WORKDIR /workspace
USER sandbox

CMD ["python", "--version"]
