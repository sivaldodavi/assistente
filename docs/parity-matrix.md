# Matriz de comportamento e testes

| Comportamento | Implementação e cobertura |
| --- | --- |
| Roteiros Case, Projeto de Paper e Paper Final, campos, opções, limites, progresso e checklists | `config/academic_workflows.json`; `test/models/academic_workflow_test.rb`, `test/models/project_test.rb`, `test/integration/projects_test.rb` |
| Salvamento, revisão concorrente, conversão Paper Final e isolamento de projetos | `app/controllers/projects_controller.rb`; `test/integration/projects_test.rb`, `test/models/project_test.rb` |
| Prévia HTML e exportação Quarto/Typst/ABNT | `app/services/document_export.rb`; `test/services/document_export_test.rb`, `test/integration/exports_test.rb`; PDF real validado no container de produção |
| Login Google, state, PKCE S256, nonce, validação do ID token e isolamento da conta | `app/lib` e controllers de autenticação; `test/integration/authentication_test.rb`, `test/controllers/omniauth_callbacks_controller_test.rb`, `test/lib/google_oauth2_strategy_test.rb` |
| Perfil acadêmico, termos, consentimentos e configurações da conta | `app/models/account.rb`, `app/controllers/account_settings_controller.rb`; `test/integration/account_settings_test.rb` |
| Biblioteca Pessoal, fichamentos e vínculo de fontes aos projetos | `app/controllers/sources_controller.rb`; `test/integration/sources_test.rb`, `test/integration/projects_test.rb` |
| Assistência contextual e avaliação formativa | `app/services/ai_workflow.rb`, `app/services/jev_rubric.rb`; `test/integration/project_assist_test.rb`, `test/integration/projects_test.rb` |
| Pacotes Pix, idempotência, webhook assinado, créditos e reconciliação de pedidos | `app/services/payment_service.rb`, `app/controllers/mercado_pago_webhooks_controller.rb`; `test/integration/payments_test.rb`, `test/services/payment_reconciliation_test.rb` |
| Administração, auditoria, páginas e conteúdo público | controllers e views correspondentes; `test/integration/admin_test.rb`, `test/integration/public_pages_test.rb` |
| Datas de entrega do Case: início de cada etapa, cronograma no PDF, validação de formato e avisos de ordem | `config/academic_workflows.json`, `app/models/project.rb`, `app/services/document_export.rb`; `test/models/academic_workflow_test.rb`, `test/models/project_test.rb`, `test/services/document_export_test.rb` |
| Grupos do debate, descrição acessível dos campos (`aria-describedby`) e vínculo das alternativas vazias à etapa 2.1 | `app/views/projects/show.html.erb`; `test/integration/projects_test.rb` |
| Auditoria do webhook pelo status do pagamento consultado, com `error_code` apenas para divergências | `app/controllers/mercado_pago_webhooks_controller.rb`; sem teste dedicado novo, cobertura indireta por `test/integration/payments_test.rb` |
| Renderização Quarto isolada e helpers de escape Typst/Markdown | `app/services/document_export/quarto_renderer.rb`, `app/services/document_export/text_formatting.rb`; `test/services/document_export_test.rb`, `test/integration/exports_test.rb` |
| Datas de entrega do projeto de paper e do paper final, com cronograma no PDF, obrigatoriedade e aviso de ordem | `config/academic_workflows.json`, `app/models/project.rb`, `app/services/document_export.rb`; `test/models/academic_workflow_test.rb`, `test/models/project_test.rb`, `test/services/document_export_test.rb`, `test/integration/projects_test.rb` |
| Chat geral de orientação sobre método, estrutura, formatação e normas, sem redigir nem avaliar o trabalho | `app/services/writing_guide.rb`, `app/controllers/writing_guide_controller.rb`, `app/views/writing_guide/show.html.erb`; `test/integration/writing_guide_test.rb` |
| Limite de solicitações por conta nas rotas de IA, no chat e na exportação em PDF | `app/controllers/concerns/rate_limitable.rb`, `app/controllers/project_assist_controller.rb`, `app/controllers/projects_controller.rb`; `test/integration/writing_guide_test.rb` |
| Testes do webhook (código de erro só para divergências) e dos caminhos de erro do renderer (Quarto indisponível e limite de renderizações) | `test/integration/payments_test.rb`, `test/services/document_export_renderer_test.rb` |
| Smoke test do PDF no CI | `.github/workflows/ci.yml` (job `pdf-smoke`) |

Os testes de integrações usam doubles locais para provedores externos. Para confirmar operações do Mercado Pago, use o ambiente sandbox e não crie cobranças reais de teste.
