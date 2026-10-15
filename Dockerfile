FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY surecheck_mcp.py /app/surecheck_mcp.py
USER 65534:65534
ENTRYPOINT ["python", "/app/surecheck_mcp.py"]
