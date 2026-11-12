# Assistente Acadêmico

Reconstrução Rails do Assistente Acadêmico. O `main` contém a configuração separada de staging e produção. A produção está publicada em `https://trab.sivaldodavi.com.br`: páginas informativas são públicas, o login Google está habilitado e as áreas de conta exigem sessão.

## Stack

- Ruby 3.4 e Rails 8.1
- SQLite
- ERB, CSS e JavaScript servidos pelo Propshaft
- Quarto/Typst como ferramentas externas de geração acadêmica

## Estado operacional

Verificado em 12/11/2026: o container de produção está saudável; `/`, `/planos`, `/ajuda-ia`, `/termos` e `/privacidade` responderam HTTP 200. O login Google real já foi concluído em produção. A imagem contém Quarto 1.11.9 e Typst 0.15.1; uma exportação PDF real foi gerada e validada no container ativo. Os timers de reconciliação de pagamentos e de backup estão habilitados e ativos. Nenhuma cobrança real foi criada para teste.

## Desenvolvimento local

```sh
bin/rails db:prepare
bin/rails server
```

O login Google usa OmniAuth com state, PKCE (S256), nonce OIDC descartável e verificação de ID token/email. Em produção, o host de retorno é fixado em `https://trab.sivaldodavi.com.br`; configure o cliente OAuth para o callback `https://trab.sivaldodavi.com.br/auth/google_oauth2/callback`. Login de desenvolvimento existe apenas nos ambientes `development` e `test`; não há Devise nem login por senha.

### Configuração de integrações

| Integração | Configuração |
| --- | --- |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` ou credenciais Rails em `google.*`. |
| DeepSeek | `DEEPSEEK_API_KEY` ou `DEEPSEEK_API_KEY_FILE` (padrão `/run/secrets/deepseek_api_key`); `DEEPSEEK_API_URL`, `DEEPSEEK_MODEL` e `DEEPSEEK_TIMEOUT` são opcionais. |
| JEV TypeSafe | `TYPESAFE_API_KEY` ou `TYPESAFE_API_KEY_FILE` (padrão `/run/secrets/typesafe_api_key`); `TYPESAFE_API_URL`, `TYPESAFE_MODEL` e `JEV_TIMEOUT` são opcionais. |
| Mercado Pago | `MERCADOPAGO_ACCESS_TOKEN` e `MERCADOPAGO_WEBHOOK_SECRET`, ou seus respectivos `*_FILE` (padrão em `/run/secrets/`). A URL HTTPS pode ser `mercadopago.webhook_url`, `MERCADOPAGO_WEBHOOK_URL` ou `BASE_URL`; os caminhos aceitos são `/webhooks/mercadopago` e `/api/mercadopago/webhook`. |
| Administração | `ADMIN_EMAILS`: lista de e-mails separada por vírgula. |

As chaves de IA também podem ser armazenadas nas credenciais Rails em `ai.deepseek_api_key` e `ai.typesafe_api_key`; as de pagamento em `mercadopago.access_token` e `mercadopago.webhook_secret`. Não coloque segredos em arquivos rastreados ou no banco de dados. A criação do Pix é iniciada pela conta autenticada e os pacotes, preços e créditos são definidos no servidor.

Para configurar a cópia local com um assistente que deixa os valores visíveis para conferência e os salva criptografados, execute:

```sh
bin/rails runner script/configure_credentials.rb
```

O script preserva entradas existentes como `secret_key_base`, aceita valores em branco para manter ou pular campos e exige confirmação digitando `SIM`. A digitação aparece no terminal e no histórico visual da sessão; use apenas em uma máquina confiável e não compartilhe a tela. `config/master.key` existe neste checkout e é ignorado pelo Git; mantenha-o protegido. No servidor, forneça a chave mestra como `RAILS_MASTER_KEY` e injete os segredos por ambiente ou arquivos Docker em `/run/secrets`. Este projeto não carrega `.env` automaticamente.

O modo público informativo pode ser reativado com `AUTHENTICATION_READY=false`: o Caddy encaminha as rotas ao Rails, cujo `ProductionAccessGate` retorna `503` para login, callback, áreas autenticadas e Pix, mantendo páginas informativas e webhook disponíveis. Em modo funcional, `AUTHENTICATION_READY=true` libera o OmniAuth e os controllers; cada área privada exige sessão e o webhook de produção valida assinatura. O Caddyfile principal importa `/config/assistente-academico.Caddyfile`, sincronizado a partir do fragmento versionado em `deploy/production/Caddyfile`; o endpoint legado de staging não deve ser direcionado ao container de produção.

## Roteiros

`config/academic_workflows.json` define os roteiros de Case, Projeto de Paper e Paper Final, com 10, 9 e 6 etapas, respectivamente. Projetos são associados à conta, com salvamento, controle de revisão concorrente e conversão de Projeto de Paper em Paper Final. O Case permite registrar apenas as datas de entrega do relatório, do debate e da dissertação; a dissertação é escrita em um único campo. A Biblioteca Pessoal mantém fontes e fichamentos privados e permite vinculá-los aos projetos. A exportação acadêmica oferece prévias HTML e PDFs via Quarto/Typst com o modelo ABNT de referência.

Contas, Google OAuth, isolamento por proprietário, perfil, termos e consentimentos estão implementados. A exclusão confirmada da conta remove também projetos, revisões, fontes e dados associados; não há recurso de exportação dos dados da conta.

## Escopo funcional acordado

Implementados: assistência contextual de escrita, avaliação formativa separada, pagamentos por Pix com pacotes/créditos usando o SDK Ruby oficial (`mercadopago-sdk`), administração e páginas públicas de pacotes, termos, privacidade e explicação da IA. Pagamentos e IA usam adaptadores de serviço e testes com doubles locais.

Foram excluídos definitivamente desta reconstrução: agenda e tarefas com datas livres, lembretes automáticos, compartilhamento e comentários administrativos, recomendações jurídicas, e-mails/outbox, fallback de provedores, promoção/desconto e exportação dos dados da conta. Permanecem as três datas fixas do Case e a exportação acadêmica HTML/PDF.

As páginas públicas estão em `/`, `/planos` (também `/plans`), `/termos`, `/privacidade` e `/ajuda-ia`. No modo funcional, o login Google e compras Pix ficam disponíveis a contas autenticadas. A política identifica Sivaldo Davi Pereira como responsável e informa `contato@sivaldodavi.com`, contato já publicado no site pessoal do responsável. Os avisos legais continuam sendo um rascunho funcional e devem ser revisados.

As integrações externas foram habilitadas após autorização explícita. O login Google real foi concluído em produção. Credenciais Mercado Pago de produção foram verificadas; a entrega de uma notificação nativa ainda precisa ser confirmada no painel. Nenhuma cobrança real foi criada para teste. Um pagamento Pix em produção movimenta dinheiro real. Os testes automatizados usam doubles locais; use o sandbox para testes de compra. A [matriz de paridade](docs/parity-matrix.md) registra os comportamentos cobertos, as exclusões e as validações externas pendentes.

## Testes

```sh
bin/rails test
bin/rubocop
bin/rails zeitwerk:check
```

O port da matriz de testes da fonte original ainda está em andamento. O OAuth iniciou o fluxo real até o Google, mas o callback precisa de validação pelo usuário no navegador. Mercado Pago de produção respondeu à verificação de credenciais; nenhuma cobrança foi criada. Use sandbox para testes financeiros.

## Staging e banco

O SQLite de desenvolvimento fica em `storage/development.sqlite3`; testes usam `storage/test.sqlite3`. Em produção, `DATABASE_PATH` define o arquivo; o padrão é `storage/production.sqlite3`. O compose `deploy/staging/docker-compose.yml` monta um volume durável e se conecta à rede externa `servidor_default`. Ele espera `SECRET_KEY_BASE` em `/opt/servidor/secrets/assistente-academico/rails.env` e os arquivos `mercadopago_access_token` e `mercadopago_webhook_secret` nesse diretório. Mantenha-os fora do Git e restrinja as permissões.

Esse compose mantém o gate de autenticação fechado e injeta apenas credenciais sandbox do Mercado Pago. O serviço de staging permanece definido para retomada controlada, mas não deve reiniciar automaticamente nem ter uma rota pública enquanto estiver parado. Não exponha a porta do Rails no host.

O compose de produção (`deploy/production/docker-compose.yml`) é separado do staging e usa outro volume persistente, credenciais e diretório de segredos. Por autorização do responsável, mantém `AUTHENTICATION_READY=true` por padrão e `GOOGLE_OAUTH_TEST_READY=false`; o compose de staging mantém o gate fechado. O fragmento Caddy versionado em `deploy/production/Caddyfile` deve ser copiado para `/config/assistente-academico.Caddyfile` no volume persistente do Caddy, e `/opt/servidor/Caddyfile` deve importá-lo; esse caminho interno é necessário porque o container monta o Caddyfile principal, mas não o checkout Rails. Mantenha a configuração versionada junto ao projeto. O arquivo `rails.env` deve ficar em `/opt/servidor/secrets/assistente-academico-production/rails.env` com `SECRET_KEY_BASE`, `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` em `root:root`, modo `600`. Os quatro arquivos montados como segredos (`mercadopago_access_token`, `mercadopago_webhook_secret`, `deepseek_api_key` e `typesafe_api_key`) devem pertencer a UID/GID `1000:1000`, modo `400`, para leitura pelo usuário Rails do container; a pasta pai permanece `root:root`, modo `700`, fora do alcance dos usuários do host. Não reutilize os segredos sandbox.

Para adicionar credenciais de produção do Mercado Pago sem tocar no staging, selecione **Produção** em Suas integrações > aplicação > Credenciais e obtenha o Access Token. O segredo de assinatura fica em Webhooks > Configurar notificações no ambiente de produção. Confira o seletor: tokens de teste e produção podem ter prefixos semelhantes. O instalador `ruby script/configure_production_mercadopago.rb` mostra os valores digitados, pede confirmação dupla e envia somente os dois segredos por SSH; ele não inicia serviços, não altera o Caddy e recusa sobrescrever arquivos existentes. A rota `https://trab.sivaldodavi.com.br/webhooks/mercadopago` já aponta para o container de produção; a entrega nativa pelo painel ainda precisa ser confirmada. Não cole credenciais no chat.

Para produção, use o callback Google `https://trab.sivaldodavi.com.br/auth/google_oauth2/callback`, credenciais OAuth/MP específicas de produção e segredos fora do Git. O container está saudável e `AUTHENTICATION_READY=true`; contas privadas exigem sessão e o webhook exige assinatura válida. O login Google foi validado em navegador. Ainda falta confirmar uma notificação nativa do Mercado Pago e testar compras somente no sandbox. Não crie pagamentos de produção para teste. Os textos legais estão publicados e ainda precisam de revisão.

O arquivo do banco nunca deve ser commitado. Faça backups consistentes em destino protegido, confirme permissões e teste a restauração em ambiente isolado.

Pedidos Pix pendentes podem ser reconciliados com `bin/rails payments:reconcile`. A tarefa verifica pedidos sem atualização há pelo menos cinco minutos, consulta o pagamento pelo ID salvo ou pesquisa pelo identificador externo e só concede créditos após validar a resposta pelo mesmo serviço idempotente do webhook. Ausência de resultado não cancela o pedido; somente um estado terminal confirmado pelo Mercado Pago o encerra. A tarefa verifica até 100 pedidos por execução. O timer systemd de produção está habilitado para executá-la a cada dez minutos; falhas ficam no journal e fazem a tarefa terminar com erro.

Para produção em systemd, os arquivos `deploy/production/assistente-academico-reconcile.service` e `.timer` executam a tarefa Rails a cada dez minutos no container de produção, sem criar pagamentos. Acompanhe a execução com `journalctl -u assistente-academico-reconcile.service`.

Backups diários de produção são criados por `deploy/production/assistente-academico-backup.timer`. O serviço usa o SQLite `.backup` pelo container, verifica `PRAGMA integrity_check`, grava arquivos `0600` em `/opt/servidor/backups/assistente-academico-production/daily/` (diretório `0700`) e mantém as sete cópias diárias mais recentes. Backups de pré-publicação e snapshots de infraestrutura ficam separados e não são removidos por essa rotação.

```sh
docker exec assistente-academico-production sqlite3 /rails/storage/production.sqlite3 ".backup '/tmp/assistente-academico.sqlite3'"
docker cp assistente-academico-production:/tmp/assistente-academico.sqlite3 /opt/servidor/backups/assistente-academico-production/
```

Verifique cada cópia com `PRAGMA integrity_check` e teste restaurações em arquivo isolado. O timer preserva sete cópias diárias e os backups anteriores fora do diretório `daily`; não copie o banco ativo com `cp` comum.

## Git e publicação

O repositório mantém somente a branch compartilhada `main`, com commits Conventional Commits em português. Valide mudanças antes de publicar; nenhum deploy ocorre sem autorização explícita.
