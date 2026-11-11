"""Small, auditable guardrails for navigation and UI automation."""
import os
import re
from urllib.parse import urlsplit


class BrowserSecurityError(ValueError):
    pass


def check_url(url: str, allowed_hosts: str | None = None) -> str:
    if not isinstance(url, str) or len(url) > 4096:
        raise BrowserSecurityError("URL inválida ou longa demais")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError as exc:
        raise BrowserSecurityError("URL malformada") from exc
    if parsed.scheme not in {"http", "https"} or not host:
        raise BrowserSecurityError("Somente HTTP/HTTPS são permitidos; file:, data:, javascript: bloqueados")
    if parsed.username or parsed.password:
        raise BrowserSecurityError("Credenciais embutidas na URL são proibidas")
    if allowed_hosts is None:
        allowed_hosts = os.environ.get("OMNI_BROWSER_ALLOWED_HOSTS", "")
    hosts = [h.strip().lower().rstrip(".") for h in allowed_hosts.split(",") if h.strip()]
    if hosts and not any(host == h or host.endswith("." + h) for h in hosts):
        raise BrowserSecurityError(f"Domínio não permitido: {host}")
    return url


def validate_repo_name(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", value):
        raise BrowserSecurityError("Nome do repositório inválido")
    if value in {".", ".."} or value.endswith(".git"):
        raise BrowserSecurityError("Nome de repositório inválido")
    return value


def validate_owner(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", value):
        raise BrowserSecurityError("Owner GitHub inválido")
    return value


HIGH_IMPACT = re.compile(r"(?:delete|remove|erase|buy|pay|purchase|transfer|publish|create repository|send payment|delete account|excluir|apagar|comprar|pagar|publicar|criar repositório)", re.I)


def check_sensitive_click(selector: str, confirm: bool) -> None:
    if HIGH_IMPACT.search(selector) and not confirm:
        raise BrowserSecurityError("Clique potencialmente irreversível: passe confirm=true após revisar a ação")
