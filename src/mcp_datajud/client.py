from __future__ import annotations

import os
from typing import Any, Dict, List

from .errors import APIError, APIRateLimitError, AuthenticationError, NotFoundError
from .generator import build_dynamic_client
from .http_client import DataJudSession
from .logging_config import get_json_logger
from .parser import APIParser


class DataJudClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api-publica.datajud.cnj.jus.br",
    ) -> None:
        api_key = api_key or os.getenv("DATAJUD_API_KEY")
        if not api_key:
            raise ValueError("É necessário fornecer a chave da API DataJUD via parâmetro ou variável de ambiente DATAJUD_API_KEY")
        self.logger = get_json_logger()
        self.session = DataJudSession(api_key=api_key, base_url=base_url)
        self._parser = APIParser(self.session)
        self._api_spec: Dict[str, Any] = self._parser.load_spec()
        self._client = build_dynamic_client(self._api_spec, self.session)

    # MCP: descobre ferramentas
    def list_tools(self) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []
        tribunais: Dict[str, Any] = self._api_spec.get("tribunais", {})
        for tribunal, t_spec in tribunais.items():
            category_name = t_spec.get("display_name", tribunal.upper())
            for method in t_spec.get("methods", []):
                tool_entry = {
                    "tool_name": method.get("tool_name"),
                    "category": category_name,
                    "description": method.get("summary", "") + " - " + t_spec.get("description", ""),
                    "input_schema": method.get("parameters", {}),
                }
                tools.append(tool_entry)
        return tools

    # MCP: executa uma ferramenta
    def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            if "." not in tool_name:
                return {"error": "Nome de ferramenta inválido. Use o formato categoria.metodo (ex.: tjsp.buscar_processos)."}
            category, method = tool_name.split(".", 1)
            category_obj = getattr(self._client, category, None)
            if category_obj is None:
                return {"error": f"Categoria '{category}' não encontrada."}
            method_to_call = getattr(category_obj, method, None)
            if method_to_call is None:
                return {"error": f"Método '{method}' não encontrado em '{category}'."}

            result = method_to_call(**kwargs)
            return result if isinstance(result, dict) else {"data": result}

        except APIRateLimitError:
            return {"error": "A solicitação não pôde ser completada pois o limite de chamadas à API foi excedido. Por favor, tente novamente mais tarde."}
        except AuthenticationError:
            return {"error": "Falha na autenticação. Verifique se sua chave da API está correta e válida."}
        except NotFoundError:
            return {"error": "O recurso solicitado não foi encontrado. Verifique se os identificadores fornecidos estão corretos."}
        except APIError as e:
            return {"error": f"Erro da API: {e.message}"}
        except TypeError as e:
            return {"error": f"Parâmetros inválidos para a ferramenta: {e}"}
        except Exception as e:
            return {"error": f"Erro inesperado: {e}"}
