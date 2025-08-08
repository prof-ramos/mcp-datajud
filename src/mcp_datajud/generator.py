from __future__ import annotations

import inspect
import types
import keyword
from typing import Any, Callable, Dict

from .http_client import DataJudSession


def generate_docstring(tribunal: str, description: str, input_schema: Dict[str, Any]) -> str:
    lines = [
        f"Buscar processos no {tribunal.upper()} via API DataJUD.",
        "",
        description or "",
        "",
        "Args:",
    ]
    properties: Dict[str, Any] = input_schema.get("properties", {})
    for name, meta in properties.items():
        t = meta.get("type", "any")
        d = meta.get("description", "")
        default = meta.get("default")
        default_str = f" (padrão: {default})" if default is not None else ""
        lines.append(f"  - {name} ({t}){default_str}: {d}")
    return "\n".join(lines)


def _sanitize_param_name(name: str) -> str:
    if not name.isidentifier() or keyword.iskeyword(name):
        return f"{name}_"
    return name


def build_signature_from_schema(input_schema: Dict[str, Any]) -> inspect.Signature:
    params = []
    properties: Dict[str, Any] = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
        "null": type(None),
    }

    seen_names: set[str] = set()
    for original_name, meta in properties.items():
        is_required = original_name in required
        py_type = meta.get("type")
        if isinstance(py_type, list):
            annotation = tuple(type_map.get(t, object) for t in py_type)
        else:
            annotation = type_map.get(py_type, object)

        default = inspect._empty if is_required else meta.get("default", None)
        name = _sanitize_param_name(original_name)
        # Evitar colisões
        while name in seen_names:
            name = f"{name}_"
        seen_names.add(name)

        params.append(
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )

    # Permitir kwargs livres (additionalProperties)
    params.append(
        inspect.Parameter(
            name="_extra",
            kind=inspect.Parameter.VAR_KEYWORD,
        )
    )

    return inspect.Signature(params)


def create_api_method(session: DataJudSession, http_method: str, path: str, tribunal: str, input_schema: Dict[str, Any], description: str) -> Callable[..., Any]:
    def api_call(self, **kwargs: Any) -> Dict[str, Any]:
        # Parâmetros especiais de paginação do cliente
        pagina = kwargs.pop("pagina", None)
        buscar_todas = kwargs.pop("buscar_todas_paginas", False)

        # Montar corpo da requisição ES
        body: Dict[str, Any] = {}
        for key in ("query", "sort", "size", "from", "search_after"):
            if key in kwargs and kwargs[key] is not None:
                body[key] = kwargs[key]

        # Conveniência: se página for informada, ajustar 'from'
        if pagina is not None:
            size = int(body.get("size", 10))
            page_index = max(int(pagina) - 1, 0)
            body["from"] = page_index * size

        # Execução simples (uma página)
        if not buscar_todas:
            return session.request(method=http_method, path=path, json_body=body)

        # Buscar todas as páginas (ingênuo com from/size; para grandes volumes, preferir search_after)
        size = int(body.get("size", 1000))
        size = max(1, min(size, 10000))
        from_offset = int(body.get("from", 0))
        aggregated_hits: list[Any] = []

        while True:
            page_body = dict(body)
            page_body["from"] = from_offset
            page_body["size"] = size
            resp = session.request(method=http_method, path=path, json_body=page_body)
            hits = (
                resp.get("hits", {}).get("hits", [])
                if isinstance(resp, dict)
                else []
            )
            aggregated_hits.extend(hits)
            if len(hits) < size:
                # Última página
                return {"data": aggregated_hits, "pagination": {"fetched": len(aggregated_hits)}}
            from_offset += size

    api_call.__doc__ = generate_docstring(tribunal, description, input_schema)
    api_call.__name__ = f"buscar_processos"
    api_call.__signature__ = build_signature_from_schema(input_schema)
    return api_call


def build_dynamic_client(api_spec: Dict[str, Any], session: DataJudSession) -> Any:
    root = types.SimpleNamespace()

    for tribunal, t_spec in api_spec.get("tribunais", {}).items():
        category_cls = type(tribunal.upper(), (object,), {})
        category_obj = category_cls()

        for method_spec in t_spec.get("methods", []):
            api_method = create_api_method(
                session=session,
                http_method=method_spec.get("http_method", "POST"),
                path=method_spec.get("path"),
                tribunal=tribunal,
                input_schema=method_spec.get("parameters", {}),
                description=method_spec.get("summary", ""),
            )
            setattr(category_obj, "buscar_processos", types.MethodType(api_method, category_obj))

        setattr(root, tribunal, category_obj)

    # Anexar metadados para introspecção
    setattr(root, "__api_spec__", api_spec)
    return root
