# Arquitetura da aplicação

A aplicação é um monólito Python pequeno. A aplicação web renderiza HTML com Jinja; JavaScript existe para comportamento local, não para reconstruir toda a interface a partir de JSON. SQLite pertence somente à aplicação.

## Fronteiras

- `routes/`: HTTP, autenticação da requisição e composição da resposta.
- `domain/`: regras puras e normalização, sem Flask, banco ou provedor externo.
  - `domain/types.py` - Contratos TypedDict para todos os modelos de dados (Fase 3)
  - `domain/case.py`, `domain/paper.py` - Regras de roteiros Case e Paper
  - `domain/workflow.py` - Seções, conferências, entregas, desenvolvimento
  - `domain/case_rubric.py` - Rubricas e checklists para JEV
  - `domain/schedule.py` - Cronograma de entregas
  - `domain/legal_recommendations.py` - Normalização de requisições jurídicas
- `store/`: SQLite, transações e consultas.
- `services/`: integrações externas e operações que cruzam domínios.
- `config.py` - Constantes centralizadas (timeouts, limites, headers, etc.) (Fase 3)
- Não há `workers/` na aplicação atual; tarefas assíncronas não fazem parte do produto publicado.
- `templates/`: experiência visual e acessibilidade.
- `static/`: CSS e módulos de interação local.

Cada módulo deve ter uma responsabilidade que possa ser descrita em uma frase. Se uma rota começa a carregar regra de negócio ou HTML muito grande, a mudança deve ser feita na fronteira correta, não escondida em um helper genérico.

## Estado e persistência

Dados do usuário pertencem ao projeto ou à conta de forma explícita. Snapshots acadêmicos podem usar JSON validado, mas proprietário, revisão, permissões, reservas de uso e status de notificações são estruturados.

Autosave usa revisão otimista. Nenhuma resposta velha pode sobrescrever uma revisão nova. A interface sempre informa salvando, salvo, conflito ou erro.

## Integrações

DeepSeek, JEV/Typesafe, Google OAuth e Quarto ficam atrás de serviços com contratos pequenos. O contato manual de atendimento não é um provedor da aplicação. Testes substituem cada provedor por fake. Valores secretos nunca entram em código ou logs.

### Timeouts de provedores (Fase 2)

Todos os timeouts são configuráveis via variáveis de ambiente:
- `PROVIDER_TIMEOUT` (padrão 30s) - base para todos
- `DEEPSEEK_TIMEOUT` (padrão 30s)
- `GEMINI_TIMEOUT` (padrão 30s)
- `JEV_TIMEOUT` (padrão 60s)

### AbortController no frontend (Fase 2)

Requisições de IA suportam cancelamento via `AbortController`:
- Apenas uma requisição ativa por vez
- Indicador visual de loading com spinner
- Tratamento gracioso de `AbortError`

### Contratos tipados (Fase 3)

Todos os modelos de dados usam `TypedDict` em `app/domain/types.py`:
- `AIContext`, `AIResponse`, `AISuggestionItem`, `AIChecklistItem`
- `JEVSectionResult`, `JEVReportResult`, `JEVValidationResult`, `JEVExplanation`
- `ProviderResponse`, `ProviderUsage`
- `ProjectPayload`, `CriterionDict`, `DevelopmentSectionDict`, etc.
- `AccountProfile`, `ProjectSharingPreferences`
- `CatalogEntry`, `CatalogSearchResult`
- `RateLimitAction`, `RateLimitInfo`

### Configuração centralizada (Fase 3)

Todas as constantes em `app/config.py`:
- Limites de campos, contagens máximas, timeouts
- Rate limiting (`RATE_LIMITS`, `RATE_LIMIT_WINDOW_SECONDS`, `_RATE_LIMIT_MAX_KEYS`)
- Headers de segurança (`SECURITY_HEADERS`)
- Planos, catálogo jurídico, revisões, exclusão, paginação

## Design System Visual (Fase 4 - Outubro 2026)

Refatoração completa do design system para corrigir inconsistências visuais reportadas em produção:

### Tokens (`static/css/tokens.css`)
- **Tipografia**: escala base aumentada (xs 12px → **md 15px** body padrão) + tipografia fluida `clamp()` para body (`--text-body: clamp(15px, 1vw, 17px)`, `--text-body-sm: clamp(13px, 0.9vw, 15px)`)
- **Contraste dark mode**: `--color-text-muted: #c0c0c0` (era #a0a0a0), `--color-text-dim: #909090` (era #737373) - WCAG AA
- **Spacing scale**: gaps preenchidos com `--space-13` a `--space-30` (valores pares)
- **Focus ring**: `3px` width / `4px` offset (era 2px/3px invisível em dark)
- **Z-index**: dropdown `55` > modal `50` (corrigido dropdown cortado por modal)
- **Sidebar tokens**: `--sidebar-width: 220px`, `--sidebar-width-collapsed: 64px`
- **Containers semânticos**: `--container-content: 760px`, `--container-form: 900px`, `--container-wide: 1100px`

### Layout & Containers (`app.css`, `editor.css`, `marketing.css`, `profile.css`, `admin.css`)
- Referências legadas `--container-*` substituídas por tokens semânticos
- Sidebar responsiva em `editor.css`: breakpoints 1100px (colapsada), 900px (expandida), 680px (mobile drawer)
- Pricing grid 2-col em `marketing.css` (~1000px)
- Library grid proporção natural em `app.css`

### Componentes (`app.css`, `editor.css`, `marketing.css`)
- **Hardcoded borders**: `#393939` → `var(--color-border-strong)` em `editor.css`
- **Select reset**: `appearance: none`, seta SVG customizada, tokens de cor/bg
- **Botões padronizados**: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`
- **Empty state**: componente `.empty-state` com ícone, título, texto, ação
- **User email**: `.user-email` com truncamento `text-overflow: ellipsis`
- **FAQ padding**: aumentado para `var(--space-20)` vertical
- **Timeline connector**: pseudo-element `::before` vertical em `.sales-journey-list`
- **Mockup containers**: tipografia legível, tags visíveis, `overflow: hidden`, `text-overflow: ellipsis`
- **Footer spacing**: margins e line-height corrigidos

### Templates (`templates/account/home.html`, `templates/public/home.html`)
- **13 redundâncias removidas**: menu topbar duplicado, botão "Sair" duplicado, textos descritivos, títulos repetidos, labels excessivos mockup, "Ver exemplo"/"Ver exemplos" unificados
- **WhatsApp**: integrado ao footer, removido bloco isolado
- **Pricing cards**: simplificados (removido "Projetos: X", "Assinatura")
- **FAQ**: removido texto introdutório longo
- **Mockup/buttons**: limpo mockup, mantidos botões fora
- **Tipos**: "Escolha o roteiro inicial" → "Roteiro inicial", "Veja trabalhos preenchidos" → "Exemplos práticos"
