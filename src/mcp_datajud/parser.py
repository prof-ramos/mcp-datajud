from __future__ import annotations

import os
from typing import Any, Dict, List

from .http_client import DataJudSession


DEFAULT_TRIBUNAIS: List[str] = [
    # Amostra; pode ser configurado via env VAR DATAJUD_TRIBUNAIS (separados por vírgula)
    "tjsp", "tjmg", "tjrs", "tjpr", "tjba", "tjpe",
    "trt1", "trt2", "trt3", "trt4", "trt5",
]


class APIParser:
    def __init__(self, session: DataJudSession) -> None:
        self.session = session

    def load_spec(self) -> Dict[str, Any]:
        tribunais_csv = os.getenv("DATAJUD_TRIBUNAIS")
        tribunais = [t.strip().lower() for t in tribunais_csv.split(",") if t.strip()] if tribunais_csv else DEFAULT_TRIBUNAIS

        spec: Dict[str, Any] = {"tribunais": {}}
        for tribunal in tribunais:
            # Em produção, poderíamos buscar mapeamentos para enriquecer o schema.
            # Aqui, definimos uma ferramenta canônica por tribunal: buscar_processos (POST /api_publica_{tribunal}/_search)
            spec["tribunais"][tribunal] = {
                "name": tribunal,
                "display_name": tribunal.upper(),
                "endpoint": f"/api_publica_{tribunal}/_search",
                "description": f"Busca processos no {tribunal.upper()} usando consulta Elasticsearch.",
                "methods": [
                    {
                        "tool_name": f"{tribunal}.buscar_processos",
                        "http_method": "POST",
                        "path": f"/api_publica_{tribunal}/_search",
                        "summary": f"Buscar processos no {tribunal.upper()}",
                        "parameters": self._default_input_schema(),
                    }
                ],
            }
        return spec

    def _default_input_schema(self) -> Dict[str, Any]:
        # Schema MCP-like (JSON Schema subset) aceitando corpo Elasticsearch
        return {
            "type": "object",
            "properties": {
                "query": {"type": "object", "description": "Consulta Elasticsearch (bool/match/range etc.)"},
                "sort": {"type": ["array", "object"], "description": "Ordenação Elasticsearch"},
                "size": {"type": "integer", "default": 10, "minimum": 1, "maximum": 10000},
                "from": {"type": "integer", "default": 0, "minimum": 0},
                "search_after": {"type": ["array", "null"], "description": "Cursor para paginação eficiente"},
                # Controles adicionais do cliente (não enviados como-is):
                "pagina": {"type": ["integer", "null"], "minimum": 1, "description": "Página 1-based para conveniência"},
                "buscar_todas_paginas": {"type": "boolean", "default": False},
            },
            "required": [],
            "additionalProperties": True,
        }
