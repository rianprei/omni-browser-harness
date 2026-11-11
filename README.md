# Omni Browser Harness

**Browser harness local, gratuito e open source (MIT)**, baseado em Playwright + Chromium. Não usa Browser Use, serviços pagos, tokens de API ou uma conta de automação externa.

## Recursos

- Browser real Chromium, sessões persistentes em perfil isolado (cookies e login ficam somente no computador).
- CLI com abertura, snapshot semântico e fluxo GitHub `github-create` com dry-run e confirmação.
- Servidor **MCP stdio** com 13 ferramentas: navegação, leitura, snapshots, cliques, formulários, abas, capturas e criação de repositório GitHub.
- Integração com **Claude Code**, **Codex CLI** e outros clientes MCP locais.
- `--push-from` para enviar um projeto Git ao repositório criado (requer autenticação Git separada).
- Proteções básicas: sem armazenamento de senhas no código; perfis com permissões restritas; navegação apenas HTTP(S); domínios configuráveis; confirmação para criação de repositório e alguns cliques sensíveis.

## Requisitos

Python >=3.10 e Chromium (ou Chrome) instalado. Linux, Windows ou macOS com suporte Playwright. O script `scripts/install.sh` foi feito para Linux/macOS; no Windows use os comandos Python equivalentes.

## Instalação Linux

```bash
unzip omni-browser-harness.zip
cd omni-browser-harness
bash scripts/install.sh
source .venv/bin/activate
```

O script cria um virtualenv e instala `playwright`. Se não houver Chromium/Chrome no PATH, instala o Chromium gerenciado pelo Playwright. Nenhum serviço remoto é exigido.

## Criar `rianprei/omni-research-oss`

1. Faça login manual numa janela separada do Chromium. **Não cole senhas no ChatGPT nem na linha de comando**.

```bash
omni-browser login
```

2. Faça primeiro um teste sem criar nada:

```bash
omni-browser github-create --owner rianprei --name omni-research-oss --public
```

3. Confirme a criação do repositório (faz uma ação real na sua conta):

```bash
omni-browser github-create --owner rianprei --name omni-research-oss --public --apply
```

4. Para fazer push do OmniResearch anteriormente preparado, extraia `omni-research-oss-github-ready.zip` num diretório e inicialize o Git caso tenha usado o ZIP (o Git bundle preserva o histórico). Depois:

```bash
omni-browser github-push --source /caminho/omni-research-oss --owner rianprei --name omni-research-oss --apply
```

ou use `--push-from` no comando `github-create`. **O login do browser não autentica o Git CLI.** Configure Git Credential Manager, chave SSH com remote SSH, ou GitHub CLI de forma independente antes do push.

### Limitações da criação de repositórios

O GitHub atualiza frequentemente a interface. Se o formulário mudar, a automação interrompe em vez de supor opções ou afirmar sucesso. **A criação só é confirmada se a URL final corresponder a `https://github.com/{owner}/{name}`.** Não há bypass de CAPTCHA, 2FA, restrições da conta ou login.

## MCP para Claude Code e Codex

Instale o projeto e registre o servidor local. Exemplo Claude Code:

```bash
claude mcp add omni-browser -- /caminho/omni-browser-harness/.venv/bin/python -m omni_browser.mcp_server
```

Para Codex, adapte `examples/codex-config.toml` para o Python do virtualenv. Configurações JSON em `examples/claude-mcp.json`.

O MCP executa **no computador que inicia o cliente**. Ele não roda automaticamente nesta conversa hospedada no ChatGPT, nem dá acesso ao navegador pessoal para o assistente sem uma conexão local autorizada. Este harness não hospeda um MCP HTTP público.

## Segurança e privacidade

- O **perfil do browser contém cookies de login**, mantenha o diretório sob seu controle. Nunca o envie ao GitHub nem compartilhe em ZIPs.
- Perfis persistentes não devem ser compartilhados entre processos concorrentes e não devem apontar para o perfil principal do Chrome.
- Configure `OMNI_BROWSER_ALLOWED_HOSTS=github.com` para limitar navegação externa no MCP. Valores separados por vírgulas. Domínios subalternos são aceitos; não use um host-curinga.
- `browser_click` é automação de UI, **não é uma sandbox de segurança completa**: cliques e formulários podem ter efeitos mesmo com a heurística de confirmação. Revise o que o agente faz e as permissões dos sites.
- Saída é produzida apenas para o cliente MCP via stdout, sem logs de cookies/credenciais.
- `github_create_repository` exige `confirm: true` após `github_prepare_repository`. Ações no GitHub seguem as regras normais da conta.
- Não expor este processo MCP sem autenticação em rede pública.

## Testes

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

Testes incluem segurança, validação, protocolos e simulações do formulário GitHub. Testes de navegação real devem ser realizados no ambiente do usuário com rede e sessão permitidas.

## Base técnica

Playwright (Apache-2.0) e Chromium (licenças de software livre). Este projeto é original, MIT; não reproduz código do navegador nem scripts proprietários.
