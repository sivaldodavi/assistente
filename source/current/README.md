# Assistente Acadêmico

Aplicação do Assistente Acadêmico, construída em Python, Flask, Jinja, SQLite, JavaScript modular e Quarto. O código, o banco e o repositório da aplicação são independentes do sistema legado.

## Princípio de desenvolvimento

A aplicação é construída em percursos verticais privados. Cada percurso precisa de documentação, teste de contrato e dados temporários antes de receber uma integração externa. O login de desenvolvimento só existe quando `ASSISTENTE_V2_ALLOW_DEV_AUTH=1` ou quando a aplicação é criada com `ALLOW_DEV_AUTH=True` nos testes; ele nunca é uma forma de autenticação de produção.

## Desenvolvimento

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
flask --app wsgi:app run --debug
```

A aplicação usa `instance/data/assistente_v2.sqlite3` por padrão. Para testes, use um caminho temporário definido pela fixture. O nome interno `ASSISTENTE_V2_*` permanece como contrato de configuração para não quebrar ambientes já preparados; ele não representa uma segunda aplicação pública.

## Configuração externa

Copie `.env.example` apenas para um ambiente local. Os valores reais nunca entram no Git. DeepSeek, Gemini, JEV/Typesafe, Google OAuth e Quarto entram por adaptadores de serviço e configuração segura; o catálogo jurídico entra por volume externo somente leitura; o contato manual de atendimento é externo e não é integrado ao sistema; testes usam substitutos falsos. A chave Gemini é opcional e só é consultada quando uma ação estruturada do editor encontra falha técnica ou resposta inválida do DeepSeek. No VPS, ela deve ser colocada no arquivo secreto montado como `/run/secrets/gemini_api_key`, conforme `docs/ia/PROVEDORES-IA.md`; nunca no template, no JavaScript ou no banco.

### Variáveis de ambiente suportadas (Fases 1-3)

```env
# Timeouts de IA (Fase 2)
PROVIDER_TIMEOUT=30          # Timeout base para todos os provedores (segundos)
DEEPSEEK_TIMEOUT=30          # Timeout específico DeepSeek
GEMINI_TIMEOUT=30            # Timeout específico Gemini
JEV_TIMEOUT=60               # Timeout específico JEV/Typesafe

# Security & Rate Limiting (Fase 0 + Fase 3)
# Headers CSP, HSTS, Permissions-Policy, COOP/COEP aplicados via middleware
# Rate limiting in-memory por ação: project-create, ai-analysis, jev-evaluation, etc.

# Configuração centralizada (Fase 3) - app/config.py
# Todos os limites, timeouts, headers, planos, catálogo, revisões, paginação
```

## Operação publicada

O domínio público `https://trab.sivaldodavi.com.br` usa o serviço `site-assistente-academico`. O banco novo fica em `/opt/servidor/data/assistente-academico/assistente_v2.sqlite3`. O código e os dados anteriores permanecem disponíveis em `/opt/servidor/sites/assistente-academico-legado/` e `/opt/servidor/data/assistente-academico-legado/`; o legado não é iniciado pelo domínio principal.

O backup diário do banco é mantido pelo timer `assistente-db-backup.timer`. Ele valida a cópia e uma restauração temporária antes de mantê-la, com retenção de 14 dias. Leia `docs/ia/OPERACAO-BACKUP.md` antes de alterar banco, deploy ou recuperação.

## Arquitetura (resumo)

```
app/
├── config.py              # Configuração centralizada (Fase 3)
├── domain/
│   ├── types.py           # Contratos TypedDict (Fase 3)
│   ├── case.py            # Regras de roteiro Case
│   ├── paper.py           # Regras de roteiro Paper
│   ├── workflow.py        # Seções, conferências, entregas
│   ├── case_rubric.py     # Rubricas e checklists JEV
│   └── legal_recommendations.py
├── services/
│   ├── providers.py       # DeepSeek, Gemini, JEV clients (Fase 2: timeouts configuráveis)
│   ├── ai_workflows.py    # Composição de contexto e validação
│   ├── ai_support.py      # Limites de campos, IDs dinâmicos
│   ├── legal_recommendations.py
│   ├── research.py        # Catálogo jurídico
│   └── quarto.py          # Exportação PDF Quarto/Typst
├── store/                 # SQLite, transações, consultas
├── routes/                # HTTP, auth, composição de resposta
├── auth.py                # Google OAuth + PKCE, rate limiting, security headers
└── templates/             # Jinja2 templates
```

## Frontend (Fase 1)

```
static/
├── css/
│   ├── tokens.css         # Design tokens centralizados
│   ├── app.css            # Estilos base usando tokens
│   ├── editor.css         # Editor de projetos
│   ├── marketing.css      # Vitrine pública
│   ├── admin.css          # Painel admin
│   ├── library.css        # Biblioteca pessoal
│   └── profile.css        # Perfil da conta
└── js/
    ├── autosave.js        # Salvamento automático otimista
    ├── project-schedule.js # Editor de cronograma
    ├── project-ai.js      # Assistência IA contextual (Fase 2: AbortController)
    ├── pdf-export.js      # Exportação Quarto
    ├── duplicate.js       # Duplicação de projetos
    ├── revisions.js       # Histórico de revisões
    └── jev-panel.js       # Painel JEV (seção, relatório, explicação)
```

## Princípios do produto

O usuário verá o mesmo tipo de editor, etapas e documentos do site atual. A implementação é diferente: templates server-side, módulos pequenos, operações explícitas e testes por contratos de fluxo. A IA fica dentro das etapas: pode revisar campos, sugerir pergunta-problema, teses, critérios e referências, ler checklists e chamar o JEV para avaliação orientativa. Nenhuma sugestão altera o texto sem confirmação. A descrição dos fatos permanece na etapa própria do Case; não existe módulo de cronologia. Os modelos públicos completos são mantidos em `app/domain/public-models.json`, com conteúdo anonimizado portado do legado.

## Funcionalidades implementadas

### Fase 0: Segurança (Concluída)
- 23 issues de segurança resolvidas
- CSP, HSTS, Permissions-Policy, COOP/COEP headers
- Google OAuth com PKCE, state, nonce
- Rate limiting in-memory granular por ação
- SQLite WAL mode, migrações versionadas (v12)

### Fase 1: UX/Design System (Concluída)
- Design tokens centralizados (`static/css/tokens.css`)
- CSS refatorado usando tokens em 6 arquivos
- JavaScript modularizado em 7 ES Modules
- Acessibilidade e responsividade preservadas

### Fase 2: Operational IA/PDF (Concluída)
- Timeouts configuráveis para todos os provedores IA
- AbortController no frontend para cancelamento de requisições
- Loading spinner CSS animado
- Fallback DeepSeek → Gemini → JEV preservado

### Fase 3: Quality/Maintainability (Concluída)
- Contratos TypedDict em `app/domain/types.py`
- Configuração centralizada em `app/config.py`
- Eliminação de constantes mágicas
- Tipagem estática para contratos entre camadas

### Fase 4: Deploy/Docs (Em andamento)
- Documentação atualizada
- Deploy VPS com Docker Compose + Caddy
- Quarto CLI + Typst/ABNT no container

## Verificação mínima

```sh
python3 -m pytest -q
python3 -m compileall -q app ops wsgi.py
```

O build Docker e a medição de RAM entram antes de qualquer pré-produção. O domínio atual só muda após aceite explícito e rollback testado.

O backup diário deve ser mantido por uma única rotina versionada em `ops/assistente-db-backup`; não criar cópias paralelas ou alterar retenção, caminho e permissões sem atualizar também `services/assistente-db-backup.*` e `docs/ia/OPERACAO-BACKUP.md`.
