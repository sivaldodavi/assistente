# Administração manual

Administradores são definidos por `ASSISTENTE_V2_ADMIN_EMAILS`; não existe promoção automática da primeira conta. `/admin/accounts` permite listar contas, atribuir selos de plano, ajustar créditos e bloquear acesso. `/admin/projects` mostra conteúdo apenas de trabalhos cujo proprietário autorizou leitura.

## Planos e créditos

Os códigos de plano são `livre`, `avulso_ai`, `sem_ia` e `com_ia`. Alterar plano não modifica saldo silenciosamente. O formulário de créditos define o saldo desejado; `project_limit = project_used + saldo`, limitado a 1.000. Criar um trabalho registra consumo em `project_used`. A aplicação de limites na criação e os controles completos de uso de IA precisam seguir os contratos do produto de referência; não apresentar a simples existência desses contadores como prova de equivalência integral.

As colunas administrativas são aplicadas aditivamente em `app/store/db.py`, preservando contas, projetos e dados acadêmicos. O schema novo contém as mesmas colunas. A concessão é manual, com POST e CSRF; não existe checkout, confirmação Pix nem liberação por pagamento automático.

## Bloqueio e conteúdo privado

Conta bloqueada não inicia login Google/de desenvolvimento nem continua uma sessão autenticada: o próximo acesso protegido invalida a sessão e devolve 403. O store impede bloquear a própria sessão administrativa ou a única conta administradora configurada.

Listagens de contas e projetos mostram identidade e metadados, não payload acadêmico. A rota de conteúdo devolve 404 se `allow_admin_view` não estiver autorizado; comentários dependem também de `allow_admin_comments`. Ser administrador não substitui consentimento do titular.

## Organização

`app/store/admin.py` contém mutações e consultas de administração; `app/routes/admin.py` contém formulários e autorização; `templates/admin/` e `static/css/admin.css` contêm apresentação. `tests/test_admin_accounts.py` cobre CSRF, permissões, concessão, proteção contra bloqueio da própria conta e acesso somente a conteúdo compartilhado.
