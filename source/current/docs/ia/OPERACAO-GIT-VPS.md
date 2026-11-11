# Git e stagit no VPS

## Repositórios

O repositório principal da aplicação é o bare repository:

```text
/home/git/repos/assistente-academico.git
```

O remoto de desenvolvimento é chamado `vps`:

```text
ssh://root@159.223.136.31/home/git/repos/assistente-academico.git
```

A URL de navegação Git é:

```text
git://git.sivaldodavi.com.br/assistente-academico.git
```

Para clonar com acesso SSH do usuário `git`, use:

```sh
git clone git@git.sivaldodavi.com.br:/home/git/repos/assistente-academico.git
```

O nome `assistente-academico-v2.git` não existe mais. O repositório acima é o principal; `assistente-academico-legado.git` é somente a referência preservada.

O sistema anterior permanece separado em:

```text
/home/git/repos/assistente-academico-legado.git
```

Esse repositório é referência e recuperação controlada. Seu hook atualiza somente o índice do stagit e não publica o domínio principal.

## O que um push faz

O hook `post-receive` do repositório principal atualiza somente a página do histórico no stagit. O push não cria imagem Docker, não muda Caddy, não reinicia serviço e não toca em banco ou secrets. A publicação é feita separadamente pelo comando de deploy, após testes e validação.

O histórico principal fica em `/opt/servidor/data/stagit/assistente-academico/`. O histórico anterior fica em `/opt/servidor/data/stagit/assistente-academico-legado/`.

## Fluxo normal

```sh
git status --short --branch
python3 -m pytest -q
git push vps main
```

Depois do push, confirme o commit remoto:

```sh
ssh root@159.223.136.31 \
  'git --git-dir=/home/git/repos/assistente-academico.git rev-parse --short refs/heads/main'
```

## Publicação

O checkout `/opt/servidor/work/assistente-academico/` é uma cópia de trabalho para inspeção e staging; ele não é a fonte automática da publicação. O comando de deploy lê a referência indicada diretamente do bare repository, extrai-a para uma área temporária, substitui `/opt/servidor/sites/assistente-academico/` e reconstrói o serviço `site-assistente-academico` usando os Compose principal, override e `docker-compose.production.yml`.

O diretório `/opt/servidor/sites/assistente-academico-legado/` e seu Compose de recuperação ficam fora desse fluxo. Nunca use o hook do legado para publicar a aplicação principal.

O comando permanente é `/opt/servidor/deploy-site assistente-academico main`. Sua fonte versionada é `ops/deploy-site`: valida arquivos Python, templates e assets, mantém banco e secrets fora do diretório publicado e usa os três Compose de produção. Não usar o validador Hugo do aplicativo anterior.

O catálogo de pesquisa fica em `/opt/servidor/data/assistente-academico/catalogs/`, montado separadamente em `/catalogs:ro`, com `RESEARCH_CATALOG_PATH=/catalogs/catalog.sqlite3`. É o acervo externo existente, não o banco de usuários. O caminho antigo do catálogo no diretório de dados `-legado` pode apontar por symlink para esse acervo, evitando duplicação e preservando a referência anterior. Nunca apontar o banco principal ou legado para o mesmo SQLite de contas.

Os secrets do Assistente ficam em `/opt/servidor/secrets/assistente-academico/`. O arquivo `gemini_api_key` é opcional para o fallback e deve permanecer fora do Git. Em produção, o serviço roda como UID/GID numérico `10001:10001`, que também precisa ser o proprietário dos quatro secrets e do volume SQLite; isso é necessário porque a versão de Docker Compose do VPS ignora `uid`, `gid` e `mode` na declaração de secrets. Use modo `0400` nos secrets e modo `0750` no diretório do banco.

### Variáveis de ambiente de produção (Fases 1-3)

O deploy de produção deve configurar as seguintes variáveis no arquivo `.env` do compose de produção:

```env
# Timeouts de IA (Fase 2)
PROVIDER_TIMEOUT=30
DEEPSEEK_TIMEOUT=30
GEMINI_TIMEOUT=30
JEV_TIMEOUT=60

# Security headers já aplicados via middleware Flask (Fase 0)
# Rate limiting in-memory por ação (Fase 3)
# Design tokens e CSS modularizados (Fase 1) - sem config adicional
# TypedDict contracts (Fase 3) - sem config adicional
# Config centralizada em app/config.py (Fase 3) - sem config adicional
```

### Requisitos do container para Quarto (Fase 2)

O Dockerfile de produção deve incluir Quarto CLI com extensões Typst e ABNT:

```dockerfile
# Instalar Quarto
RUN wget -qO- https://quarto.org/download/latest/quarto-linux-amd64.deb > /tmp/quarto.deb && \
    apt-get update && apt-get install -y /tmp/quarto.deb && \
    rm /tmp/quarto.deb

# Instalar extensão ABNT para Typst
RUN quarto add quarto-ext/typst-abnt
```

Memória recomendada: 2GB+ para o container da aplicação (Quarto + Typst + IA).

Depois de um deploy, confirmar `/healthz`, imports OAuth e monitor local. Alterações em units systemd precisam ser instaladas explicitamente; copiar código por si só não reinstala as units.
