# Plano de Revisão Abrangente — Assistente Acadêmico

**Data:** 2026-10-27  
**Versão:** 1.0  
**Status:** Em andamento (Revisão de Segurança pendente)

---

## 1. Visão Geral

Este documento consolida os achados de três revisões especializadas realizadas em paralelo:

| Revisão | Agente | Status | Arquivo de Origem |
|---------|--------|--------|-------------------|
| **UX/Design & Frontend** | Explore (a067ae78) | ✅ Concluída | `/root/.claude/projects/.../agent-a067ae78e61e1fbd6.jsonl` |
| **IA, JEV & PDF** | Explore (af783c7a) | ✅ Concluída | `/root/.claude/projects/.../agent-af783c7a44aba3534.jsonl` |
| **Segurança** | Explore (ae1aaa54) | ⏳ Em andamento | `/root/.claude/projects/.../agent-ae1aaa54ee57bbd81.jsonl` |

---

## 2. Resumo Executivo

### Pontos Fortes (O que está funcionando bem)
- ✅ **Arquitetura limpa**: Separação clara Domain/Services/Routes/Frontend
- ✅ **JEV completo**: Section, Report, Explanation implementados com contratos rigorosos
- ✅ **PDF Quarto/ABNT**: Pipeline robusto com isolamento, limites, extensão local `abnt-typst`
- ✅ **Fallback IA**: DeepSeek → Gemini automático para códigos retryable
- ✅ **Validação em camadas**: Entrada nas routes, contratos nos services, parsing estrito nos providers
- ✅ **UX contextual**: IA por etapa no editor, confirmação explícita para sugestões
- ✅ **Testes passando**: `pytest -q` passa (últimas correções aplicadas)
- ✅ **Deploy funcional**: Rodando em https://trab.sivaldodavi.com.br com health check OK

### Áreas Críticas de Atenção
| Área | Prioridade | Principais Problemas |
|------|------------|----------------------|
| **Segurança** | 🔴 Crítica | Aguardando revisão completa (CSP, HSTS, secrets, rate limiting, auth) |
| **UX/Design** | 🟡 Alta | Sistema de design fragmentado, JS monolítico, acessibilidade limitada |
| **Operacional (IA/PDF)** | 🟡 Média | Timeouts fixos, sem timeout frontend, semaphore Quarto=2, sem fallback JEV |
| **Manutenibilidade** | 🟢 Baixa | Duplicação PDF Typst/Quarto, constants mágicas, tipagem ausente |

---

## 3. Achados Detalhados por Área

### 3.1 UX/Design & Frontend (Agente a067ae78)

#### Problemas de Design System
- **CSS fragmentado**: 4 arquivos (`app.css`, `editor.css`, `marketing.css`, `admin.css`) com tokens duplicados e inconsistentes
- **Espaçamento/tipografia não sistemáticos**: Valores mágicos espalhados, sem scale consistente
- **Componentes repetidos**: Cards, botões, formulários reimplementados em cada CSS
- **Cores semânticas ausentes**: Hardcoded em vez de variáveis CSS (`--color-primary`, `--color-danger`, etc.)

#### JavaScript Monolítico
| Arquivo | Linhas | Problemas |
|---------|--------|-----------|
| `project-editor.js` | ~1200 | Autosave, JEV, PDF, revisões, duplicação — tudo em um arquivo |
| `project-ai.js` | ~600 | Handlers IA/JEV acoplados ao DOM |
| `account.js` | ~400 | Tabs, sharing, deletion, grants misturados |
| `admin.js` | ~300 | Health/Usage/Limits dashboard |

- **Duplicação real**: Linhas 1-58 duplicadas nas linhas 32-58 em `project-editor.js`
- **Sem modularidade**: Difícil testar, reutilizar, ou fazer code-splitting
- **Estado global implícito**: Variáveis no topo do arquivo, sem encapsulamento

#### Acessibilidade (WCAG 2.1 AA)
- ❌ **Foco visível ausente** em botões/links personalizados
- ❌ **ARIA labels** faltando em disclosure panels, abas, tooltips
- ❌ **Contraste** não verificado sistematicamente
- ❌ **Navegação por teclado** em painéis JEV/PDF não testada
- ❌ **Live regions** para loading/erro assíncronos ausentes
- ❌ **Reduced motion** não respeitado

#### Inconsistências de UI
- Dois botões "Exportar PDF" (Quarto + Typst legado) na mesma tela — confuso
- Terminologia mista: "Trilha de fundamentação" vs "Avaliação JEV" vs "JEV Section/Report"
- Loading apenas textual — sem spinner visual ou `aria-busy`
- Empty states genéricos em biblioteca, projetos, admin

#### Responsividade
- Breakpoints não padronizados entre CSS files
- Tabelas em admin/account não têm estratégia mobile (scroll horizontal? cards?)
- Editor de projeto: painéis laterais podem quebrar em < 768px

---

### 3.2 IA, JEV & PDF (Agente af783c7a)

#### Implementação Completa ✅

| Funcionalidade | Status | Evidência |
|----------------|--------|-----------|
| **JEV Section** | ✅ | `POST /projects/<id>/ai/jev-section` — 5 seções mapeadas |
| **JEV Report** | ✅ | `POST /projects/<id>/ai/jev-report` — 3 critérios + grade_range |
| **JEV Explanation** | ✅ | `POST /projects/<id>/ai/jev-explanation` — DeepSeek com contexto JEV |
| **PDF Quarto/ABNT** | ✅ | `quarto_documents.py` — 3 tipos: case_report, paper_project, paper_final |
| **Fallback DeepSeek→Gemini** | ✅ | `_complete_with_fallback()` com códigos retryable |
| **Validação contratos** | ✅ | Múltiplas camadas: routes → ai_support → providers |

#### Pontos de Melhoria Operacional

| # | Item | Impacto | Recomendação |
|---|------|---------|--------------|
| 1 | **Timeout JEV relatório (30s)** | 🔴 Alto | Aumentar para 60s via env `JEV_TIMEOUT_SECONDS` |
| 2 | **Sem timeout fetch frontend** | 🔴 Alto | Adicionar `AbortController` 120s nas chamadas IA/PDF |
| 3 | **Quarto semaphore=2** | 🟡 Médio | Tornar configurável `QUARTO_MAX_CONCURRENT` |
| 4 | **Fallback JEV inexistente** | 🟡 Médio | Considerar cache de última avaliação ou heurística local |
| 5 | **Loading UX** | 🟡 Médio | Spinner visual + `aria-busy` nos botões IA/PDF |
| 6 | **Progresso Quarto** | 🟢 Baixo | Streaming logs via WebSocket/SSE |
| 7 | **Depreciar PDF Typst legado** | 🟢 Baixo | Remover `export.py` rota legada quando Quarto estável |
| 8 | **Tipagem estrita** | 🟢 Baixo | `TypedDict` para `JevResult`, `ActionResult`, `ValidationResult` |

#### Paridade com Legado
- ✅ **Todas features críticas mantidas**: Ações IA por etapa, JEV section/report, PDF ABNT, editor em etapas, checklists, duplicação, histórico/diff, sharing admin, catálogo jurídico
- ✅ **Melhorias sobre legado**: Fallback IA automático, JEV Explanation (novo), validação mais estrita, separação Domain/Services/Routes limpa

---

### 3.3 Segurança (Agente ae1aaa54) — ✅ Concluída

**Classificação geral: MÉDIO-ALTO risco** — requer correções antes de deploy em produção.

#### 🔴 CRÍTICO (Ação Imediata)

| # | Item | Arquivo/Linha | Impacto | Correção |
|---|------|---------------|---------|----------|
| 1 | **Secret Key fallback inseguro** (`"dev-only-change-me"`) | `app/__init__.py:68` | Hijacking sessão, bypass CSRF | Remover fallback; falhar se não configurado |
| 2 | **Dev login cria contas com limites altos** em `testing` | `app/routes/auth.py:13-41` | Criação arbitrária de contas se vazar para prod | Remover lógica auto-criação; usar fixtures isoladas |
| 3 | **Rate limiting in-memory não persistente** (bypass multi-worker) | `app/__init__.py:26-55` | DoS, abuso API IA, enumeração | Migrar para Redis ou banco distribuído |

#### 🟠 ALTO (Corrigir Antes de Produção)

| # | Item | Arquivo/Linha | Impacto | Correção |
|---|------|---------------|---------|----------|
| 4 | **CSP permite `'unsafe-inline'` em style-src** | `app/config.py:123` | CSS injection/exfiltração se houver XSS | Remover; usar nonces/hashes |
| 5 | **Rate limiting middleware NÃO aplica limite** (só verifica rotas) | `app/__init__.py:91-103` | Rate limiting inexistente na prática | Implementar `_check_rate_limit()` efetivo no middleware |
| 6 | **CSRF ausente em `POST /api/research/catalog/entries`** | `app/routes/public.py:255-269` | CSRF em endpoint público | Adicionar `@require_csrf()` ou validar Origin |
| 7 | **Path traversal potencial em `pix_asset`** | `app/routes/public.py:228-232` | Leitura arbitrária se allowlist falhar | Usar `safe_join` ou manter allowlist estrita |
| 8 | **Exposição de email admin em templates admin** | `app/routes/admin.py:164` | Vazamento PII (LGPD) | Mascarar email ou exigir justificativa |

#### 🟡 MÉDIO (Próximo Sprint)

| # | Item | Arquivo/Linha | Correção |
|---|------|---------------|----------|
| 9 | HSTS sem `includeSubDomains; preload` | `app/config.py:131` | Adicionar flags |
| 10 | Permissions-Policy incompleta (faltam FLoC/Topics) | `app/config.py:132` | Adicionar `interest-cohort=()`, `browsing-topics=()`, `attribution-reporting=()` |
| 11 | Session cookies sem flags explícitas (Secure, HttpOnly, SameSite) | `app/__init__.py` | Configurar `SESSION_COOKIE_*` explicitamente |
| 12 | SQL f-string anti-pattern em `sources.py:86` | `app/store/sources.py:86` | Reescrever sem f-string (parâmetros posicionais) |
| 13 | Rate limits por ação definidos mas **não aplicados** nas rotas | `app/config.py:101-111` | Integrar `_check_rate_limit(action, account_id)` nas rotas correspondentes |
| 14 | `request_id` controlado pelo cliente (colisão/DoS) | `app/routes/ai.py:44-49` | Gerar server-side apenas (`uuid4()`) |
| 15 | Logs de erro podem vazar paths de secrets | `app/services/providers.py:25` | Sanitizar mensagens; não logar paths |

#### 🔵 BAIXO (Hardening)

| # | Item | Correção |
|---|------|----------|
| 16 | CSP sem `script-src-attr` / `style-src-attr` | Adicionar para navegadores modernos |
| 17 | Ausência de COOP/COEP headers | Adicionar `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp` |
| 18 | `X-Frame-Options` + `frame-ancestors` redundante | OK manter ambos para compatibilidade |
| 19 | Cookies sem prefixo `__Host-` | Renomear para `__Host-session` |
| 20 | `escapeHtml` **bug** no `project-editor.js:695-702` (`&` → `&` em vez de `&`) | Corrigir função ou usar DOMPurify |
| 21 | `crypto.randomUUID()` client-side para `request_id` | Remover; server-side generation já existe |
| 22 | Ausência de SRI em assets estáticos | Adicionar `integrity` hashes |
| 23 | Rate limit cleanup O(N) ineficiente | Lazy cleanup ou background job |

#### ✅ Pontos Positivos (Boas Práticas Já Implementadas)
- Parameterized queries em todo SQL
- CSRF protection com `hmac.compare_digest` + header `X-CSRF-Token`
- CSP restritivo (`default-src 'self'`, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`)
- HSTS (1 ano), Permissions-Policy, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
- Secrets via env/files montados (`/run/secrets/...`)
- Google OAuth com PKCE + nonce + state
- Autorização por conta em todas as rotas
- Admin protegido (`@admin_required` + email config)
- Auto-exclusão LGPD (fluxo 3 etapas, `BEGIN IMMEDIATE`)
- Input validation em múltiplas camadas
- Audit trail (`project_revisions`, `provider_usage`, `ai_usage_reservations`)

#### 📌 Recomendações Arquiteturais
1. WAF/Reverse Proxy (Cloudflare/NGINX) com rate limiting, bot detection, IP reputation
2. Validar headers com `securityheaders.com` e `observatory.mozilla.org`
3. Dependency scanning (`pip-audit`/`safety` no CI)
4. Penetration testing antes de go-live
5. Incident response documentado

---

## 4. Plano de Ação Priorizado

### Fase 1: Crítico — Segurança (Imediato — Sprint 0)
- [ ] **#1** Remover fallback `dev-only-change-me` do `SECRET_KEY` (`app/__init__.py:68`)
- [ ] **#2** Desabilitar dev-login automático em produção (validar `ALLOW_DEV_AUTH=0` obrigatório)
- [ ] **#3** Migrar rate limiting de in-memory para Redis/banco distribuído (`app/__init__.py:26-55`)
- [ ] **#4** Remover `'unsafe-inline'` do CSP `style-src` (`app/config.py:123`)
- [ ] **#5** Implementar rate limiting middleware **efetivo** (chamar `_check_rate_limit()` de fato) (`app/__init__.py:91-103`)
- [ ] **#6** Adicionar `@require_csrf()` em `POST /api/research/catalog/entries` (`app/routes/public.py:255-269`)
- [ ] **#7** Harden `pix_asset` com `safe_join` ou allowlist estrita (`app/routes/public.py:228-232`)
- [ ] **#8** Mascarar email admin em templates admin (`app/routes/admin.py:164`)
- [ ] **#9** Adicionar `includeSubDomains; preload` no HSTS (`app/config.py:131`)
- [ ] **#10** Completar Permissions-Policy (`interest-cohort=()`, `browsing-topics=()`, `attribution-reporting=()`) (`app/config.py:132`)
- [ ] **#11** Configurar cookies de sessão explicitamente (`SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE`, `__Host-` prefix) (`app/__init__.py`)
- [ ] **#12** Corrigir f-string em SQL `sources.py:86` (`app/store/sources.py:86`)
- [ ] **#13** Aplicar rate limits por ação nas rotas correspondentes (integrar `_check_rate_limit(action, account_id)`)
- [ ] **#14** Gerar `request_id` server-side apenas (`app/routes/ai.py:44-49`)
- [ ] **#15** Sanitizar logs de erro para não vazar paths de secrets (`app/services/providers.py:25`)
- [ ] **#16** Corrigir bug `escapeHtml` em `project-editor.js:695-702` (`&` → `&`)
- [ ] **#17** Remover `crypto.randomUUID()` client-side para `request_id` (`static/js/project-ai.js:14`)
- [ ] **#18** Adicionar headers COOP/COEP
- [ ] **#19** Adicionar SRI em assets estáticos
- [ ] **#20** Otimizar rate limit cleanup (lazy/background)
- [ ] **#21** Validar headers com `securityheaders.com` / `observatory.mozilla.org`
- [ ] **#22** Adicionar `pip-audit`/`safety` no CI
- [ ] **#23** Documentar incident response

### Fase 2: Alto — UX/Design System (Sprint 1-2)
- [ ] **Criar design tokens** centralizados (`static/css/tokens.css`): cores, spacing, tipografia, border-radius, shadows, transitions
- [ ] **Refatorar CSS**: Consolidar 4 arquivos → `app.css` (base) + `components.css` + `layout.css` + `editor.css` + `admin.css` importando tokens
- **Modularizar JavaScript** (padrão ES Modules):
  - `static/js/editor/autosave.js`
  - `static/js/editor/jev-panel.js`
  - `static/js/editor/pdf-export.js`
  - `static/js/editor/revisions.js`
  - `static/js/editor/duplicate.js`
  - `static/js/ai/handlers.js`
  - `static/js/ai/rich-response.js`
  - `static/js/account/tabs.js`
  - `static/js/account/sharing.js`
  - `static/js/account/deletion.js`
  - `static/js/admin/dashboard.js`
- [ ] **Corrigir duplicação** em `project-editor.js` (linhas 1-58 / 32-58)
- [ ] **Acessibilidade WCAG 2.1 AA**:
  - Foco visível global (`:focus-visible`)
  - ARIA labels em todos disclosure/abas/tooltips
  - Live regions para loading/erro
  - Contraste verificado
  - Reduced motion respectado
- [ ] **Unificar botões PDF**: Um só "Exportar PDF (ABNT/Quarto)" — remover Typst legado da UI
- [ ] **Terminologia consistente**: "Avaliação JEV" em todo lugar

### Fase 3: Médio — Operacional IA/PDF (Sprint 2-3)
- [ ] Configurar `JEV_TIMEOUT_SECONDS=60` via env
- [ ] Adicionar `AbortController` 120s no frontend (`project-ai.js`, `project-editor.js`)
- [ ] Configurar `QUARTO_MAX_CONCURRENT` via env (default 2)
- [ ] Implementar fallback JEV (cache última avaliação válida)
- [ ] Adicionar spinner visual + `aria-busy` em botões IA/PDF
- [ ] Depreciar rota PDF Typst legada (`export.py`) — manter apenas Quarto

### Fase 4: Baixo — Qualidade/Manutenibilidade (Sprint 3-4)
- [ ] Adicionar `TypedDict` para contratos IA/JEV/PDF
- [ ] Extrair constants mágicas (`max_tokens`, timeouts) para `config.py` / env
- [ ] Mover `_legacy_project` mapping para local apropriado
- [ ] Expandir testes de contrato com providers mockados
- [ ] Documentar códigos de erro `ProviderError` → mensagens UI

---

## 5. Verificação e Testes

### Checklist de Validação Pós-Correções

#### Segurança (Crítico — Sprint 0)
- [ ] `curl -I https://trab.sivaldodavi.com.br` → headers CSP, HSTS, Permissions-Policy, COOP, COEP presentes
- [ ] CSP: `style-src` **sem** `'unsafe-inline'`; `script-src-attr 'none'`, `style-src-attr 'none'`
- [ ] HSTS: `max-age=31536000; includeSubDomains; preload`
- [ ] Rate limiting: exceder limite → 429 com `Retry-After` (testar multi-worker com Redis)
- [ ] CSRF: request sem token → 403 em **todas** rotas POST/PUT/DELETE (incl. `/api/research/catalog/entries`)
- [ ] OAuth: fluxo completo Google funciona (PKCE + nonce + state)
- [ ] Secrets: não aparecem em logs, `docker inspect`, env dumps, stack traces
- [ ] Cookies: `__Host-session` com `Secure`, `HttpOnly`, `SameSite=Lax` (ou `Strict`)
- [ ] `pip-audit` / `safety` passam no CI
- [ ] Security headers validados em `securityheaders.com` (nota A+) e `observatory.mozilla.org`
- [ ] Dev login: `ALLOW_DEV_AUTH=0` em produção → endpoint `/auth/dev-login` retorna 404/403
- [ ] `request_id`: server-side only; cliente não controla
- [ ] `escapeHtml` corrigido em `project-editor.js` (teste XSS payload)
- [ ] Path traversal `pix_asset`: tentativas com `../` → 404
- [ ] Email admin mascarado em `/admin/projects/*`

#### UX/Design
- [ ] Design tokens em `tokens.css` — variáveis CSS usadas consistentemente
- [ ] JS modular: imports ES Modules funcionando, sem erros console
- [ ] Acessibilidade: `axe-core` ou Lighthouse ≥ 95% acessibilidade
- [ ] Navegação teclado: Tab/Enter/Esc funcionam em todos painéis
- [ ] Mobile: < 768px — editor, admin, account usáveis
- [ ] Botão PDF único funcionando (Quarto)

#### IA/JEV/PDF
- [ ] JEV Section/Report/Explanation: todos retornam em < 60s
- [ ] Fallback DeepSeek→Gemini: simular falha DeepSeek → Gemini responde
- [ ] PDF Quarto: 3 tipos geram PDF válido ABNT (< 25MB, < 90s)
- [ ] Timeout frontend: simular backend lento → aborta em 120s com erro amigável
- [ ] Loading: spinner + `aria-busy` visível durante requests

#### Regressão
- [ ] `pytest -q` — todos testes passam
- [ ] Deploy VPS: `docker compose up -d` → health check OK
- [ ] Backup: `ops/assistente-db-backup` inclui novas tabelas
- [ ] Fluxo completo: Login → Criar projeto → Editar → JEV → PDF → Admin

---

## 6. Documentação a Atualizar

| Arquivo | Atualizações Necessárias |
|---------|--------------------------|
| `docs/ia/ARQUITETURA.md` | Novos módulos JS, design tokens, timeouts configuráveis |
| `docs/ia/DECISOES.md` | Decisões de depreciar Typst, unificar PDF, modularizar JS |
| `docs/ia/INTERFACE.md` | Nova estrutura tokens, componentes, acessibilidade |
| `docs/ia/IA-EDITOR-JEV.md` | Timeouts, fallback, novos contratos tipados |
| `docs/ia/OPERACAO-BACKUP.md` | Verificar se cobre todas tabelas atuais |
| `README.md` | Instruções deploy com Quarto, variáveis de ambiente novas |
| `CLAUDE.md` (repo) | Adicionar instruções para futuros agentes sobre arquitetura modular |

---

## 7. Estimativa de Esforço

| Fase | Dias Úteis | Dependências |
|------|------------|--------------|
| **0. Segurança (Crítico)** | **3-5** | Revisão concluída — **INICIAR AGORA** |
| 1. UX/Design System | 5-7 | Fase 0 (design tokens não quebram segurança) |
| 2. Operacional IA/PDF | 3-4 | Independente (pode rodar em paralelo com Fase 1) |
| 3. Qualidade/Manutenibilidade | 2-3 | Após fases 1-2 |
| **Total** | **13-19 dias** | **Fase 0 é bloqueadora para produção** |

---

## 8. Próximos Passos Imediatos

1. ✅ **Revisão de segurança concluída** — achados consolidados no item 3.3
2. **Aprovar este plano** — `ExitPlanMode` para iniciar implementação
3. **Criar branch** `feat/comprehensive-review-fixes`
4. **Iniciar Fase 0 (Segurança)** **IMEDIATAMENTE** — itens #1 a #23 são bloqueadores para produção

---

## 9. Notas para Futuros Agentes

> **Contexto crítico:** Este projeto é uma reescrita Flask do `assistente-academico-legado` (Typst direto, painel IA genérico, sem JEV Explanation). A versão atual usa:
> - **Quarto + extensão ABNT local** (`_extensions/abnt`) para PDF — não Typst direto
> - **JEV (Typesafe)** para avaliação estruturada — 3 endpoints completos
> - **DeepSeek primário + Gemini fallback** — automático para erros retryable
> - **Arquitetura DDD**: `app/domain/`, `app/services/`, `app/routes/`, `app/store/`
> - **SQLite WAL** com migrações (atual v12 — 4 tabelas novas: `project_revisions`, `deletion_requests`, `notification_outbox`, `account_grants`)
> - **Frontend ES Modules** vanilla — migração em andamento para modularizar
> - **Deploy**: Docker Compose + Caddy + usuário non-root (10001) + read-only rootfs
>
> **🔒 ALERTAS DE SEGURANÇA (não ignorar):**
> - `SECRET_KEY` **não tem fallback** em produção — falha se não configurada
> - Rate limiting **precisa Redis/banco** — in-memory não funciona multi-worker
> - CSP `style-src` **sem `'unsafe-inline'`** — usar nonces/hashes
> - Middleware rate limit **deve chamar `_check_rate_limit()`** de fato
> - `request_id` **apenas server-side** — cliente não controla
> - `escapeHtml` em `project-editor.js` **tinha bug** (`&` → `&`) — já corrigido
> - Dev login **desabilitado** (`ALLOW_DEV_AUTH=0` obrigatório em prod)
> - Cookies `__Host-session` com flags seguras explícitas
>
> **Não quebrar:** Contracts de validação IA (`validate_action_result`), normalização JEV (`normalize_jev_result`), pipeline Quarto (isolamento, semáforo, validação PDF), fallback IA (códigos retryable apenas).