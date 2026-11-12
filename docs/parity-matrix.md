# Matriz de paridade

A fonte é o conjunto de 134 testes Python em `recovery/original-zip`, não o snapshot Stagit. Os testes Rails consolidam comportamentos em cenários de integração e modelo; portanto, a diferença entre 134 e 84 não mede, por si só, funcionalidade ausente. As funcionalidades definitivamente excluídas pelo usuário estão listadas separadamente.

| Comportamento mantido | Testes de referência originais | Cobertura Rails atual | Estado |
| --- | --- | --- | --- |
| Roteiros Case, Projeto de Paper e Paper Final, campos, opções, limites, progresso e checklists | `test_academic_workflows.py`, `test_paper_workflows.py` | `test/models/academic_workflow_test.rb`, `test/models/project_test.rb`, `test/integration/projects_test.rb` | Coberto; a especificação JSON é comparada byte a byte com a fonte preservada. |
| Salvamento, validação, revisão concorrente, conversão Paper Final, isolamento de projetos e tarefas manuais | `test_projects.py` | `test/integration/projects_test.rb`, `test/models/project_test.rb`, `test/models/academic_schedule_test.rb` | Coberto por testes Rails. |
| Prévia HTML escapada, geração QMD/Typst/ABNT e disponibilidade de exportação por documento/fase | `test_export.py` | `test/services/document_export_test.rb`, `test/integration/exports_test.rb`, `test/integration/projects_test.rb` | Coberto com fakes nos testes; PDF real validado no container de produção em 12/11/2026 com Quarto 1.11.9 e Typst 0.15.1. |
| Sugestões contextuais DeepSeek, consentimento, contrato estruturado e avaliação JEV separada | `test_ai_workflows.py` | `test/integration/project_assist_test.rb`, `test/integration/projects_test.rb` | Coberto com doubles locais; respostas externas continuam dependentes de credenciais e validação no provedor. |
| Login Google, state, PKCE S256, nonce, verificação do ID token, CSRF, contas e isolamento | `test_oauth.py`, `test_account.py` | `test/integration/authentication_test.rb`, `test/controllers/omniauth_callbacks_controller_test.rb`, `test/integration/account_settings_test.rb`, `test/lib/google_oauth2_strategy_test.rb` | Coberto com fakes; login real concluído e confirmado em produção. |
| Biblioteca Pessoal, fichamentos privados e vínculo de fontes pertencentes à conta | `test_library.py`, parte de `test_projects.py` | `test/integration/sources_test.rb`, `test/integration/projects_test.rb` | Coberto; buscas em catálogo externo não fazem parte do escopo. |
| Agenda manual, datas, tarefas sugeridas/editáveis, status e ordenação | `test_schedule.py` | `test/models/academic_schedule_test.rb`, `test/integration/projects_test.rb` | Coberto; lembretes automáticos e filtros de calendário removidos foram excluídos. |
| Pacotes Pix, preço calculado no servidor, idempotência, webhook assinado, créditos e recuperação de pedidos ambíguos | `test_payment_orders.py`, `test_payment_security.py`, `test_payment_webhook.py`, recuperação sem promoções em `test_promotion_reconciliation.py` | `test/integration/payments_test.rb`, `test/services/payment_reconciliation_test.rb` | Coberto com doubles; o timer de reconciliação está habilitado e ativo em produção. Falta confirmar uma notificação nativa pelo painel do provedor; nenhuma cobrança real foi criada para teste. |
| Administração de planos/créditos, auditoria, bloqueio, páginas e conteúdo público | `test_admin.py`, `test_public_web.py` | `test/integration/admin_test.rb`, `test/integration/public_pages_test.rb`, `test/integration/account_settings_test.rb` | Coberto por testes Rails; os textos legais ainda precisam de revisão antes da publicação. |

## Exclusões definitivas

Não portados: compartilhamento e comentários administrativos (`test_sharing.py` e testes de compartilhamento em `test_account.py`/`test_projects.py`); recomendações jurídicas e catálogo de fontes (`test_legal_recommendations.py`); e-mail/outbox e lembretes automáticos (`test_email_outbox.py`); Gemini e fallback (`test_ai_workflows.py`); promoções, descontos e reservas de estoque (`test_payment_orders.py`, `test_payment_webhook.py` e partes promocionais de `test_promotion_reconciliation.py`); exportação de dados da conta.

## Validações externas ainda necessárias

- O callback `https://trab.sivaldodavi.com.br/auth/google_oauth2/callback` e o login Google real já foram validados em produção; segredos permanecem fora do Git.
- Confirmar uma notificação nativa de teste no painel Mercado Pago. Usar sandbox para compras de teste; nenhuma cobrança real foi criada.
- Os timers de reconciliação e backup estão habilitados e ativos; continuar observando logs e testar uma restauração SQLite em ambiente isolado.
- Revisar termos e privacidade, que já estão publicados.

Em 12/11/2026, a produção estava publicada e saudável, com páginas públicas acessíveis e áreas privadas protegidas por sessão. O staging continua fechado por padrão. A revisão legal e a confirmação da notificação nativa do provedor permanecem pendentes.
