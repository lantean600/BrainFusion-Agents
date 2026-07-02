FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app/src

COPY pyproject.toml README.md ./
COPY data ./data
COPY docs ./docs
COPY examples ./examples
COPY src ./src

CMD ["python", "-m", "brainfusion_agents", "cloud-job"]
