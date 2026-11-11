# Workflow para publicar OmniResearch no GitHub

**Objetivo:** criar `https://github.com/rianprei/omni-research-oss` e enviar o código da versão Cloud preparada anteriormente.

1. Instale o harness com `bash scripts/install.sh`.
2. Faça login manual: `omni-browser login` (o Chromium usa perfil dedicado e mantém a sessão apenas no computador).
3. Simule: `omni-browser github-create --owner rianprei --name omni-research-oss --public`.
4. Confirme: `omni-browser github-create --owner rianprei --name omni-research-oss --public --apply`.
5. Extraia `omni-research-oss-github-ready.zip`. Se extraído sem histórico Git:

```bash
git -C /caminho/omni-research-oss init -b main
git -C /caminho/omni-research-oss add .
git -C /caminho/omni-research-oss commit -m 'Initial OmniResearch OSS Cloud'
```

6. Configure o GitHub CLI ou o gerenciador de credenciais Git. A sessão do navegador não substitui autenticação Git.
7. Publique com:

```bash
omni-browser github-push --source /caminho/omni-research-oss --owner rianprei --name omni-research-oss --apply
```

8. Só depois use o repositório real para criar o serviço no Render. A configuração `render.yaml` do OmniResearch já está no projeto; o deploy depende de autorização de ações no Render e testes do endpoint.

**Nota:** este arquivo é um guia. A criação do repositório e o push não são executados ao instalar ou abrir o ZIP.
