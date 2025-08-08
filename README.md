# MCP DataJUD (Python)

Cliente MCP dinâmico para a API Pública do DataJUD (CNJ).

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Configuração

Defina a variável `DATAJUD_API_KEY` com sua chave pública.

## CLI

- Listar ferramentas:

```bash
mcp-datajud list-tools
```

- Executar uma ferramenta (params como JSON):

```bash
mcp-datajud execute tjsp.buscar_processos --params '{"query": {"match_all": {}}, "size": 5}'
```

## Server (opcional)

```bash
uvicorn mcp_datajud.server:app --host 0.0.0.0 --port 8000
```

## Código

Arquitetura em camadas: comunicação HTTP, parser, gerador dinâmico, interface MCP.
