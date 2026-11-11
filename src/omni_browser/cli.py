"""User-facing CLI. Browser login happens locally and never requests credentials."""
import argparse
import json
import os
from pathlib import Path

from .core import BrowserHarness
from .github import prepare_repository, submit_repository, push_local_project


def parser():
    p = argparse.ArgumentParser(prog="omni-browser", description="Harness Playwright gratuito e local (Chromium + MCP)")
    p.add_argument("--profile", type=Path, help="Diretório próprio para cookies/sessões")
    p.add_argument("--headless", action="store_true", help="Execução sem interface gráfica")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="Abre GitHub e aguarda login manual; não coleta senhas")
    o = sub.add_parser("open", help="Abre URL e mostra snapshot")
    o.add_argument("url")
    g = sub.add_parser("github-create", help="Prepara/cria repositório GitHub via browser")
    g.add_argument("--name", required=True)
    g.add_argument("--owner", required=True)
    vs = g.add_mutually_exclusive_group()
    vs.add_argument("--public", dest="visibility", action="store_const", const="public")
    vs.add_argument("--private", dest="visibility", action="store_const", const="private")
    g.set_defaults(visibility="public")
    g.add_argument("--description", default="")
    g.add_argument("--apply", action="store_true", help="Confirma envio de criação")
    g.add_argument("--push-from", type=Path, help="Opcional: faz git push após confirmar criação")
    push = sub.add_parser("github-push", help="Publica repo Git local existente, com credenciais Git locais")
    push.add_argument("--source", type=Path, required=True)
    push.add_argument("--owner", required=True)
    push.add_argument("--name", required=True)
    push.add_argument("--apply", action="store_true")
    sub.add_parser("mcp", help="Executa MCP stdio para agentes")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "mcp":
        from .mcp_server import main as mcp_main
        return mcp_main()
    if args.command == "github-push":
        result = push_local_project(source=args.source, owner=args.owner, name=args.name, confirm=args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    # Keep headful login always possible: --headless is ignored for login.
    with BrowserHarness(profile=args.profile, headless=False if args.command == "login" else args.headless) as browser:
        if args.command == "login":
            browser.open("https://github.com/login")
            print("Faça login diretamente na janela do Chromium. Não envie sua senha para o terminal.")
            input("Depois de concluir o login no navegador, pressione ENTER aqui para encerrar: ")
            print("Sessão salva localmente no perfil:", browser.profile)
        elif args.command == "open":
            browser.open(args.url)
            print(json.dumps(browser.snapshot(), ensure_ascii=False, indent=2))
        elif args.command == "github-create":
            prepared = prepare_repository(browser, name=args.name, owner=args.owner, visibility=args.visibility, description=args.description)
            print(json.dumps({k:v for k,v in prepared.items() if k != "snapshot"},ensure_ascii=False,indent=2))
            if not args.apply:
                print("DRY RUN: nenhum repositório foi criado. Use --apply após revisar o formulário.")
            else:
                result = submit_repository(browser, owner=args.owner,name=args.name,confirm=True)
                print(json.dumps(result,ensure_ascii=False,indent=2))
                if result.get("created") and args.push_from:
                    print(json.dumps(push_local_project(source=args.push_from,owner=args.owner,name=args.name,confirm=True),ensure_ascii=False,indent=2))
                if not result.get("created"):
                    raise RuntimeError("Criação não confirmada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
