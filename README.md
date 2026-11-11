# Assistente Acadêmico

Reconstrução Rails do Assistente Acadêmico a partir do código original preservado em `recovery/original-zip`. O código validado segue para `main` por fast-forward; o staging fica em `feat/rails-staging` e publica somente o webhook do Mercado Pago. O site completo não está liberado para acesso público.

## Stack

- Ruby 3.4 e Rails 8.1
- SQLite
- ERB, CSS e JavaScript servidos pelo Propshaft
- Quarto/Typst como ferramentas externas de geração acadêmica

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

**O site permanece bloqueado por padrão:** `AUTHENTICATION_READY` ausente ou diferente de `true` mantém as páginas da aplicação em `503`. No staging, ele é fixado em `false` e o Caddy encaminha publicamente apenas os caminhos de webhook. Só habilite `AUTHENTICATION_READY=true` depois de configurar e validar OAuth Google de produção, autorização, pagamentos e operações; essa variável não substitui esses testes.

## Roteiros

`config/academic_workflows.json` é a cópia exata da especificação original `app/domain/academic-workflows.json`. Um teste verifica seu SHA-256 para impedir mudanças acidentais em perguntas, ordem, instruções e opções. Os roteiros Case, Projeto de Paper e Paper Final têm 10, 9 e 6 etapas, respectivamente.

Os três roteiros originais mantêm perguntas, ordem, instruções e opções: Case (10 etapas), Projeto de Paper (9) e Paper Final (6). Projetos são associados à conta, com salvamento, controle de revisão concorrente, conversão de Projeto de Paper em Paper Final, agenda manual e tarefas por trabalho. A Biblioteca Pessoal mantém fontes e fichamentos privados e permite vinculá-los aos projetos. A exportação acadêmica oferece prévias HTML e PDFs via Quarto/Typst com o template ABNT preservado.

Contas, Google OAuth, isolamento por proprietário, perfil, termos e consentimentos estão implementados. A exclusão confirmada da conta remove também projetos, revisões, fontes e dados associados; não há recurso de exportação dos dados da conta.

## Escopo funcional acordado

Implementados: assistência contextual com DeepSeek como único provedor generativo (sem fallback), serviço JEV TypeSafe separado para avaliação por rubrica, Mercado Pago via Pix com pacotes/créditos usando o SDK Ruby oficial (`mercadopago-sdk`), administração e páginas públicas de pacotes, termos, privacidade e explicação da IA. Pagamentos e IA usam adaptadores de serviço e testes com doubles locais.

Foram excluídos definitivamente desta reconstrução: lembretes automáticos, compartilhamento e comentários administrativos, recomendações jurídicas, e-mails/outbox, Gemini e fallback de provedores, promoção/desconto e exportação dos dados da conta. A agenda manual e a exportação acadêmica HTML/PDF permanecem.

As páginas públicas estão em `/planos` (também `/plans`), `/termos`, `/privacidade` e `/ajuda-ia`. Os avisos legais são um rascunho funcional e precisam ser revisados pelo responsável antes de qualquer publicação.

As integrações ainda requerem validação externa com credenciais de teste e ambiente sandbox. Os testes automatizados usam doubles locais; nenhuma cobrança real será feita sem autorização explícita. A [matriz de paridade](docs/parity-matrix.md) registra os comportamentos cobertos, as exclusões e os bloqueios externos; o plano de execução atualizado fica em `~/.copilot/session-state/53a3ecdd-600f-43d3-bb11-56ba8aa7b51b/plan.md`.

## Testes

```sh
bin/rails test
bin/rubocop
bin/rails zeitwerk:check
```

O port da matriz de testes da fonte original ainda está em andamento. Google, DeepSeek, TypeSafe e Mercado Pago não foram validados com serviços externos; use credenciais de teste e sandbox apenas após a validação funcional.

## Staging e banco

O SQLite de desenvolvimento fica em `storage/development.sqlite3`; testes usam `storage/test.sqlite3`. Em produção, `DATABASE_PATH` define o arquivo; o padrão é `storage/production.sqlite3`. O compose `deploy/staging/docker-compose.yml` monta um volume durável e se conecta à rede externa `servidor_default`. Ele espera `SECRET_KEY_BASE` em `/opt/servidor/secrets/assistente-academico/rails.env` e os arquivos `mercadopago_access_token` e `mercadopago_webhook_secret` nesse diretório. Mantenha-os fora do Git e restrinja as permissões.

Esse compose mantém o gate de autenticação fechado e injeta apenas credenciais sandbox do Mercado Pago. O Caddy deve encaminhar somente `POST /api/mercadopago/webhook` e `POST /webhooks/mercadopago` para o container de staging. Não exponha a porta do Rails no host, nem habilite tráfego público para as páginas antes de validar autenticação.

O compose de produção (`deploy/production/docker-compose.yml`) é separado do staging e usa outro volume persistente, credenciais e diretório de segredos. Ele mantém `AUTHENTICATION_READY=false` por padrão. O arquivo `rails.env` deve ficar em `/opt/servidor/secrets/assistente-academico-production/rails.env` com `SECRET_KEY_BASE`, `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` em `root:root`, modo `600`. Os quatro arquivos montados como segredos (`mercadopago_access_token`, `mercadopago_webhook_secret`, `deepseek_api_key` e `typesafe_api_key`) devem pertencer a UID/GID `1000:1000`, modo `400`, para leitura pelo usuário Rails do container; a pasta pai permanece `root:root`, modo `700`, fora do alcance dos usuários do host. Não reutilize os segredos sandbox.

Para adicionar as credenciais de produção do Mercado Pago sem tocar no staging, selecione **Produção** em Suas integrações > aplicação > Credenciais e obtenha o Access Token. O segredo de assinatura fica em Webhooks > Configurar notificações, no ambiente de produção. Confira o seletor de ambiente: tokens de teste e produção podem ter prefixos semelhantes. No checkout local, execute `ruby script/configure_production_mercadopago.rb`; o script mostra os valores digitados e uma prévia, pede confirmação dupla e os envia diretamente por SSH para os arquivos de produção com modo `600`. Ele não inicia serviços, não altera o Caddy e recusa sobrescrever arquivos existentes. Não cole credenciais no chat. A URL prevista é `https://trab.sivaldodavi.com.br/webhooks/mercadopago`; não use o botão de teste do painel até o Caddy ser atualizado para encaminhar essa rota ao container de produção.

Para produção, use o callback Google `https://trab.sivaldodavi.com.br/auth/google_oauth2/callback`, credenciais OAuth/MP específicas de produção e segredos fora do Git. O segredo de assinatura do webhook de produção é distinto do sandbox. Revise os textos legais, valide login e autorização, configure backup/restore e o scheduler de reconciliação. Só então, com autorização explícita, habilite `AUTHENTICATION_READY=true` e altere o Caddy para encaminhar o tráfego ao container de produção.

O arquivo do banco nunca deve ser commitado. Faça backups consistentes em destino protegido, confirme permissões e teste a restauração em ambiente isolado.

Pedidos Pix pendentes podem ser reconciliados com `bin/rails payments:reconcile`. A tarefa verifica pedidos sem atualização há pelo menos cinco minutos, consulta o pagamento pelo ID salvo ou pesquisa pelo identificador externo e só concede créditos após validar a resposta pelo mesmo serviço idempotente do webhook. Ausência de resultado não cancela o pedido; somente um estado terminal confirmado pelo Mercado Pago o encerra. A tarefa verifica até 100 pedidos por execução e não é agendada automaticamente: configure um scheduler confiável no host para executá-la periodicamente. Falhas do provedor ficam nos logs e fazem a tarefa terminar com erro.

Para produção em systemd, use `deploy/production/assistente-academico-reconcile.service` e `.timer`; o timer executa a tarefa Rails a cada dez minutos no container de produção, sem criar pagamentos. Acompanhe a execução com `journalctl -u assistente-academico-reconcile.service`.

Para fazer um backup consistente de um banco SQLite já configurado, use a ferramenta `sqlite3` no host com um destino protegido fora do checkout:

```sh
sqlite3 /caminho/do/banco.sqlite3 ".backup '/caminho/protegido/assistente-academico.sqlite3'"
sqlite3 /caminho/protegido/assistente-academico.sqlite3 "PRAGMA integrity_check;"
```

O resultado esperado da verificação é `ok`. Restrinja acesso ao arquivo, defina retenção e criptografia no ambiente de hospedagem, e teste periodicamente uma restauração em ambiente isolado. Não copie o banco ativo com um `cp` comum quando o SQLite estiver em uso; não há rotina automática de backup configurada neste projeto.

## Git e publicação

Desenvolvimento em branches `feat/...`, `fix/...` ou `refactor/...`, com Conventional Commits em português. `main` só recebe mudanças validadas por fast-forward. Nenhum deploy ocorre sem autorização explícita.
