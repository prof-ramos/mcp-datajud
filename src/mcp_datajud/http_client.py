from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import requests

from .errors import APIError, APIRateLimitError, AuthenticationError, NotFoundError
from .logging_config import get_json_logger
from .rate_limiter import TokenBucketRateLimiter


class DataJudSession:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api-publica.datajud.cnj.jus.br",
        user_agent: str = "mcp-datajud/0.1.0 (+https://github.com)",
        rate_limit_per_sec: float = 5.0,
        burst_capacity: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.8,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout_seconds = timeout_seconds
        self.logger = get_json_logger()
        self.rate_limiter = TokenBucketRateLimiter(rate_per_second=rate_limit_per_sec, burst_capacity=burst_capacity)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"APIKey {self.api_key}",
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        attempt = 0
        last_exc: Optional[Exception] = None

        while attempt <= self.max_retries:
            attempt += 1
            acquired = self.rate_limiter.acquire(tokens=1, timeout=self.timeout_seconds)
            if not acquired:
                raise APIRateLimitError("Tempo de espera por cota de requisição expirou (cliente)")
            try:
                start = time.time()
                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    timeout=self.timeout_seconds,
                )
                duration_ms = int((time.time() - start) * 1000)

                if 200 <= resp.status_code < 300:
                    try:
                        return resp.json()
                    except Exception:
                        return {"raw": resp.text}

                # Mapear erros
                body_text = resp.text
                if resp.status_code in (401, 403):
                    raise AuthenticationError("Falha na autenticação com a API DataJUD", resp.status_code, body_text)
                if resp.status_code == 404:
                    raise NotFoundError("Recurso não encontrado na API DataJUD", resp.status_code, body_text)
                if resp.status_code == 429:
                    raise APIRateLimitError("Limite de taxa da API excedido", resp.status_code, body_text)
                if 500 <= resp.status_code < 600:
                    raise APIError("Erro temporário do servidor DataJUD", resp.status_code, body_text)
                # Outros 4xx
                raise APIError(f"Erro da API DataJUD ({resp.status_code})", resp.status_code, body_text)

            except (APIRateLimitError, AuthenticationError, NotFoundError) as exc:
                self.logger.error(
                    "Falha de requisição DataJUD",
                    extra={"tool_name": "http_client.request", "params": {"method": method, "path": path, "status": getattr(exc, "status_code", None)}},
                )
                raise
            except APIError as exc:
                # Retry apenas para 5xx
                if attempt <= self.max_retries:
                    sleep_s = self.backoff_factor * attempt
                    time.sleep(sleep_s)
                    last_exc = exc
                    continue
                raise
            except requests.RequestException as exc:
                # Erros de rede: retry
                if attempt <= self.max_retries:
                    sleep_s = self.backoff_factor * attempt
                    time.sleep(sleep_s)
                    last_exc = exc
                    continue
                raise APIError(f"Erro de rede ao acessar DataJUD: {exc}") from exc

        # Se saiu do loop sem retorno
        if last_exc:
            raise APIError(f"Falha após retries: {last_exc}")
        raise APIError("Falha desconhecida na requisição DataJUD")
