from __future__ import annotations

import json
import os
from typing import Any, Dict

import click

from .client import DataJudClient


@click.group()
def main() -> None:
    """CLI para o MCP DataJUD."""


@main.command("list-tools")
@click.option("--api-key", envvar="DATAJUD_API_KEY", help="Chave da API DataJUD")
@click.option("--base-url", default="https://api-publica.datajud.cnj.jus.br", show_default=True)
def list_tools_cmd(api_key: str | None, base_url: str) -> None:
    client = DataJudClient(api_key=api_key, base_url=base_url)
    tools = client.list_tools()
    click.echo(json.dumps(tools, ensure_ascii=False, indent=2))


@main.command("execute")
@click.argument("tool_name", type=str)
@click.option("--params", type=str, default=None, help='JSON de parâmetros (ex.: {"query": {"match_all": {}}, "size": 5})')
@click.option("--api-key", envvar="DATAJUD_API_KEY", help="Chave da API DataJUD")
@click.option("--base-url", default="https://api-publica.datajud.cnj.jus.br", show_default=True)
def execute_cmd(tool_name: str, params: str | None, api_key: str | None, base_url: str) -> None:
    client = DataJudClient(api_key=api_key, base_url=base_url)
    kwargs: Dict[str, Any] = json.loads(params) if params else {}
    result = client.execute_tool(tool_name=tool_name, **kwargs)
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
