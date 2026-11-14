---
name: assistente-academico
description: >-
  Gerencia, aplica patches, executa testes, realiza deploy, versionamento/tags de release e exporta backups (zip)
  do sistema Assistente Acadêmico na VPS (159.223.136.31). Use sempre que o usuário
  mencionar o Assistente Acadêmico, enviar patches para aplicar na VPS, criar releases/tags ou solicitar
  o zip/backup dos diretórios de código e do git para a pasta Downloads local.
---

# Assistente Acadêmico — Runbook & Automação VPS

Esta skill documenta o fluxo operacional completo do **Assistente Acadêmico** hospedado na VPS.

---

## 1. Dados de Conexão e Ambiente

* **Host**: `root@159.223.136.31`
* **Autenticação SSH**: Usa a chave SSH via agente do Bitwarden Desktop (`~/.bitwarden-ssh-agent.sock`).
  Sempre passe a variável de ambiente `SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock"` nos comandos `ssh`, `scp` ou `rsync`.
  * *Dica*: Se der erro de conexão com o agente (`Connection refused` ou `No such file or directory`), inicie o Bitwarden em segundo plano:
    ```bash
    env WAYLAND_DISPLAY=wayland-1 DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 /usr/bin/bitwarden-desktop &
    ```
* **Caminhos no Servidor**:
  * **Aplicação Rails / Checkout ativo**: `/opt/servidor/apps/assistente-academico`
  * **Repositório Git Bare (`origin`)**: `/opt/servidor/git/private/assistente-academico.git`
  * **Configuração de Produção Docker Compose**: `/opt/servidor/apps/assistente-academico/deploy/production`
  * **Nome do Container**: `assistente-academico-production`
  * **Pasta local Downloads**: `/home/sivaldo/Downloads`

---

## 2. Fluxo: Gerar Zip e Enviar para Downloads

Quando o usuário pedir para gerar o zip ou backup do assistente e mandar para `Downloads`:

1. No servidor, crie o zip agrupando o repositório git e o diretório da aplicação:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
     "cd /opt/servidor && zip -r /tmp/assistente-academico.zip git/private/assistente-academico.git apps/assistente-academico"
   ```
2. Baixe o arquivo via SCP para a pasta local `~/Downloads`:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" scp \
     root@159.223.136.31:/tmp/assistente-academico.zip ~/Downloads/
   ```
3. Remova o arquivo temporário da VPS:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
     "rm -f /tmp/assistente-academico.zip"
   ```

---

## 3. Fluxo: Aplicar Patches, Testar, Implantar e Comitar

Quando o usuário informar um novo patch (ex.: em `~/Downloads/*.patch`):

### 3.1. Enviar e Aplicar Patch
1. Localize o arquivo patch em `~/Downloads`:
   ```bash
   ls -la ~/Downloads/*.patch
   ```
2. Envie para o servidor via SCP:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" scp \
     ~/Downloads/<nome-do-patch>.patch root@159.223.136.31:/opt/servidor/apps/assistente-academico/
   ```
3. Verifique e aplique o patch no checkout:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
     "cd /opt/servidor/apps/assistente-academico && git apply --check <nome-do-patch>.patch && git apply <nome-do-patch>.patch && rm -f <nome-do-patch>.patch"
   ```

### 3.2. Rodar a Suíte de Testes
O servidor roda os testes usando a imagem Docker de build do projeto:
```bash
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "docker run --rm -u 0 -v /opt/servidor/apps/assistente-academico:/rails -w /rails -e RAILS_ENV=test production-web bin/rails test"
```
Para rodar linter / RuboCop:
```bash
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "docker run --rm -u 0 -v /opt/servidor/apps/assistente-academico:/rails -w /rails production-web bin/rubocop"
```
*Se houver falha de asserção nos testes devido a novos campos ou contagens, ajuste as asserções em `test/models/academic_workflow_test.rb` ou `test/services/document_export_test.rb` até atingir 100% de sucesso.*

### 3.3. Deploy e Operação com `bin/ops`
O repositório possui o utilitário canônico `bin/ops` que encapsula o ambiente Docker e executa verificações completas:

```bash
# Rodar testes automatizados:
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "/opt/servidor/apps/assistente-academico/bin/ops test"

# Rodar linter (RuboCop):
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "/opt/servidor/apps/assistente-academico/bin/ops lint"

# Testar saúde do container em produção (/up):
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "/opt/servidor/apps/assistente-academico/bin/ops health"

# Realizar deploy em produção (testes + build + restart + health check):
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "/opt/servidor/apps/assistente-academico/bin/ops deploy"

# Ciclo completo de Release (deploy + commit + tag anotada + push no origin):
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "/opt/servidor/apps/assistente-academico/bin/ops release vX.Y.Z 'resumo da release'"
```

### 3.4. Commit e Push
Finalize comitando e enviando para o repositório bare remoto (`origin`):
```bash
SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
  "cd /opt/servidor/apps/assistente-academico && git add . && git commit -m '<tipo>: <descrição do commit>' && git push origin main"
```
Certifique-se de que o `working tree` permaneça limpo (`git status`).

---

## 4. Fluxo: Gerenciamento de Tags e Releases (SemVer)

O projeto adota versionamento semântico estrito (SemVer) com tags Git anotadas (`vX.Y.Z`) e documentação contínua no `CHANGELOG.md` e `README.md`.

### 4.1. Convenção de Versões e Changelog
* **Padrão de Tag**: Tags anotadas no formato `vX.Y.Z` (ex.: `v0.5.2`).
* **Mensagem da Tag**: Formato `Release vX.Y.Z: <resumo da release>` (ou `Release vX.Y.Z`).
* **Arquivos a atualizar na release**:
  1. `CHANGELOG.md`: Adicionar seção `## [X.Y.Z] - AAAA-MM-DD` com subseções (`### Adicionado`, `### Alterado`, `### Corrigido`, `### Removido`).
  2. `README.md`: Atualizar a menção à versão vigente no parágrafo sobre tags/SemVer.

### 4.2. Criar Tag de Release e Publicar
Após comitar as alterações e a atualização do changelog/readme:

1. Crie a tag anotada no checkout:
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
     "cd /opt/servidor/apps/assistente-academico && git tag -a vX.Y.Z -m 'Release vX.Y.Z: <resumo>'"
   ```
2. Envie o commit e a nova tag para o repositório bare (`origin`):
   ```bash
   SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
     "cd /opt/servidor/apps/assistente-academico && git push origin main && git push origin vX.Y.Z"
   ```

### 4.3. Listar e Sincronizar Tags
Para inspecionar as tags existentes no repositório ou sincronizar o checkout com o bare:
* Listar tags existentes com descrições:
  ```bash
  SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
    "cd /opt/servidor/apps/assistente-academico && git tag -l -n"
  ```
* Sincronizar tags do bare no checkout:
  ```bash
  SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" ssh root@159.223.136.31 \
    "cd /opt/servidor/apps/assistente-academico && git fetch origin --tags"
  ```

---

## 5. Fluxo: Propostas e Especificações Futuras (docs/propostas/)

Para evitar confusões entre código em produção e ideias ou implementações de fases futuras, toda proposta técnica (RFCs, roadmaps) deve ser mantida isolada na pasta:
`/opt/servidor/apps/assistente-academico/docs/propostas/`

* **Padrão de nomenclatura**: `docs/propostas/XXX-nome-da-proposta.md` (ex.: `001-promocoes-e-cupons.md`).
* **Índice**: O arquivo `docs/propostas/README.md` mantém a tabela de índice com código, título, status e data.
* **Ciclo de vida com Branch Temporária**:
  Toda implementação de proposta deve ocorrer em branch temporária dedicada (`feature/XXX-slug`):
  1. `git checkout -b feature/XXX-slug`
  2. Implementar e validar (`bin/ops verify`)
  3. Apagar o arquivo da proposta (`git rm docs/propostas/XXX-*.md`) e atualizar o índice
  4. Merge na `main`: `git checkout main && git merge --no-ff feature/XXX-slug -m 'feat: implementa proposta XXX'`
  5. **Apagar a branch imediatamente**: `git branch -d feature/XXX-slug` (garantindo que o repo só mantenha a `main`)
  6. Release e Deploy oficial: `bin/ops release vX.Y.Z 'resumo'`
* **Estrutura de cada proposta**:
  1. Status (`Rascunho | Em Revisão | Aprovado para Implementação`)
  2. Contexto e Motivação
  3. Arquitetura e Modelagem
  4. Impactos e Pontos de Atenção (reconciliação financeira, IA, webhooks)
  5. Critérios de Aceite
  6. Decisões Pendentes de Produto


