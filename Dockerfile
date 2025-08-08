FROM python:3.11-slim-bullseye

# Compliance com padrões de segurança governamental
RUN groupadd -r mcp && useradd -r -g mcp mcp
WORKDIR /app

# Copiar metadados e código
COPY pyproject.toml README.md requirements.txt ./
COPY src/ ./src/

# Instalar dependências e o pacote
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

USER mcp

ENV SERPRO_CLOUD=true \
    LGPD_MODE=strict \
    LOG_FORMAT=json \
    MONITORING=prometheus \
    PORT=8000

EXPOSE 8000
CMD ["uvicorn", "mcp_datajud.server:app", "--host", "0.0.0.0", "--port", "8000"]
