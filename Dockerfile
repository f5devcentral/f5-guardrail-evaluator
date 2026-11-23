FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GRADIO_ANALYTICS_ENABLED=False HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home evaluator && mkdir /app/results && chown evaluator /app/results
USER evaluator
EXPOSE 7860
CMD ["guardrail-evaluator", "serve", "--host", "0.0.0.0"]
