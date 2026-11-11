"""GitHub repository creation via logged-in browser, no API token required."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from .core import BrowserHarness
from .security import BrowserSecurityError, validate_owner, validate_repo_name


def first_visible(locators):
    for loc in locators:
        try:
            if loc.count() > 0 and loc.first.is_visible(timeout=2000):
                return loc.first
        except Exception:
            continue
    raise RuntimeError("Campo GitHub não localizado. Interface mudou; inspecione o snapshot do browser.")


def _repository_name_field(page):
    return first_visible([
        page.locator('input[name="repository[name]"]'),
        page.locator("#repository_name"),
        page.get_by_role("textbox", name=re.compile("repository name", re.I)),
        page.get_by_label(re.compile("repository name", re.I)),
    ])


def _visibility_option(page, visibility):
    label = visibility.capitalize()
    return first_visible([
        page.get_by_role("radio", name=re.compile(f"^{label}$", re.I)),
        page.get_by_label(re.compile(f"^{label}$", re.I)),
        page.locator(f'input[type="radio"][value="{visibility}"]'),
        page.locator(f'#repository_visibility_{visibility}'),
    ])


def _create_button(page):
    return first_visible([
        page.get_by_role("button", name=re.compile(r"^Create repository$", re.I)),
        page.get_by_role("button", name=re.compile(r"Create repository", re.I)),
        page.locator('button[type="submit"]:has-text("Create repository")'),
    ])


def prepare_repository(harness: BrowserHarness, *, name: str, owner: str, visibility: str = "public", description: str = "") -> dict:
    name = validate_repo_name(name)
    owner = validate_owner(owner)
    if visibility not in ("public", "private"):
        raise ValueError("Visibilidade deve ser public ou private")
    harness.open(f"https://github.com/new?owner={quote(owner)}")
    page = harness._ready()
    if "/login" in page.url or "session" in page.url and "/new" not in page.url:
        raise RuntimeError("GitHub exige login: execute 'omni-browser login' em modo visível")
    _repository_name_field(page).fill(name)
    if description:
        first_visible([page.locator("#repository_description"), page.locator('input[name="repository[description]"]'),page.get_by_role("textbox", name=re.compile("description", re.I))]).fill(description[:350])
    try:
        _visibility_option(page, visibility).check()
    except Exception as e:
        # Do not click Create when visibility could not be reliably set.
        raise RuntimeError("Não consegui definir a visibilidade; revise a interface GitHub") from e
    button = _create_button(page)
    # Avoid claiming ownership is verified just because the query string requests it.
    return {"prepared": True, "repository": f"{owner}/{name}", "visibility": visibility,
            "form_url": page.url, "button_enabled": button.is_enabled(),
            "snapshot": harness.snapshot(5000)["snapshot"]}


def submit_repository(harness: BrowserHarness, *, owner: str, name: str, confirm: bool = False) -> dict:
    validate_owner(owner)
    validate_repo_name(name)
    if not confirm:
        raise BrowserSecurityError("Criação requer --apply (ou confirm=true no MCP)")
    page = harness._ready()
    if "github.com/new" not in page.url:
        raise RuntimeError("Prepare o formulário primeiro; nada foi criado")
    _create_button(page).click(timeout=15_000)
    try:
        page.wait_for_url(re.compile(r"https://github\.com/[^/]+/[^/?#]+"), timeout=20_000)
    except Exception as e:
        return {"created": False, "reason": "O GitHub não confirmou a criação; revise a página", "current_url": page.url} 
    target = f"https://github.com/{owner}/{name}"
    current = page.url.rstrip("/")
    if current != target and not current.startswith(target + "/"):
        return {"created": False, "reason": "URL de repositório diferente do owner/nome solicitados", "current_url": page.url}
    return {"created": True, "url": target}


def push_local_project(*, source: Path, owner: str, name: str, confirm: bool = False) -> dict:
    if not confirm:
        raise BrowserSecurityError("Push requer --apply")
    validate_owner(owner)
    validate_repo_name(name)
    source = Path(source).expanduser().resolve()
    if not (source / ".git").exists():
        raise RuntimeError("Diretório sem .git; extraia o projeto preparado ou inicialize um Git repo")
    def git(*args):
        p = subprocess.run(["git", "-C", str(source), *args], capture_output=True, text=True,timeout=120)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip()[:1500])
        return p.stdout.strip()
    remote = f"https://github.com/{owner}/{name}.git"
    try: existing = git("remote", "get-url", "origin")
    except RuntimeError: existing = None
    if existing and existing != remote:
        raise RuntimeError(f"O remoto origin já aponta para outro lugar: {existing}")
    if not existing:
        git("remote", "add", "origin", remote)
    branch = git("branch", "--show-current") or "main"
    git("push", "-u", "origin", branch)
    return {"pushed": True, "remote": remote, "branch": branch}
