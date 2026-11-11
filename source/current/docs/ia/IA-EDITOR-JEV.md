# IA dentro do editor

## Regra de experiência

A assistência aparece dentro da etapa que está sendo preenchida. Não existe um painel genérico separado para escolher qualquer campo. O usuário pede uma ação, o servidor salva a revisão atual, monta o contexto permitido e devolve uma resposta estruturada. Nenhuma resposta altera o projeto sozinha.

## Ações do editor

`review` revisa um campo visível e pode devolver uma explicação ou uma reescrita opcional. `chat` responde a uma pergunta sem editar campos. `suggest_problem` sugere uma pergunta-problema. `suggest_theses` sugere teses ou hipóteses possíveis. `case_structure` orienta a organização do Case. `review_criteria` revisa critérios e valores. `review_references` revisa referências pessoais selecionadas. `review_development` orienta tópicos de desenvolvimento. `checklist` lê as conferências da etapa. `debate_coach` apoia a preparação do debate do Case.

As ações são mostradas nos painéis das etapas de descrição, decisões, teses, critérios, fontes e revisão. A pesquisa jurídica contextual é uma ação própria de fundamentação: consulta o catálogo real e separa Lei, Jurisprudência e Doutrina antes de a IA justificar pertinência.

## JEV e nota orientativa

O botão JEV de uma etapa usa as checklists do Case em `app/domain/case_rubric.py`. O relatório completo usa os três critérios de conteúdo e uma faixa provável de pontos. Cada item mostra score de 0 a 3, probabilidades e observação textual. O resultado é formativo, não é nota oficial e não afirma que uma lei, jurisprudência ou doutrina está juridicamente correta.

Cada observação pode pedir uma explicação adicional. A explicação volta pelo DeepSeek/Gemini, considera a evidência do projeto e informa o que conferir; não substitui a observação nem redige o trabalho.

## Provedores

DeepSeek é a primeira tentativa para ações estruturadas e revisão inline. Gemini é chamado uma única vez quando o primário está indisponível, a chave foi recusada, não há crédito, o secret não está carregado ou a resposta estrutural é inválida. Ausência de consentimento e erro de regra não disparam fallback. JEV/Typesafe permanece como avaliador separado.

Os adaptadores estão em `app/services/providers.py`; composição de contexto e validação estão em `app/services/ai_workflows.py`; limites de campos e IDs dinâmicos estão em `app/services/ai_support.py`. A interação do editor fica em `static/js/project-ai.js`, recebendo o autosave e a navegação por injeção de dependências simples. Os testes usam transportes falsos e não chamam serviços externos.

### Timeouts configuráveis (Fase 2)

Os timeouts dos provedores são agora configuráveis via variáveis de ambiente:
- `PROVIDER_TIMEOUT` (padrão 30s) - timeout base para todos os provedores
- `DEEPSEEK_TIMEOUT` (padrão 30s) - timeout específico do DeepSeek
- `GEMINI_TIMEOUT` (padrão 30s) - timeout específico do Gemini
- `JEV_TIMEOUT` (padrão 60s) - timeout específico do JEV/Typesafe

### AbortController no frontend (Fase 2)

As requisições de IA no frontend agora suportam `AbortController`:
- Requisições em andamento podem ser canceladas pelo usuário
- Apenas uma requisição de IA ativa por vez (novas cancelam a anterior)
- Indicador visual de loading com spinner animado
- Tratamento gracioso de `AbortError` (não mostra erro ao usuário)

## Contratos de tipos (Fase 3)

Todos os modelos de dados da IA são agora tipados com `TypedDict` em `app/domain/types.py`:
- `AIContext` - contexto completo enviado aos provedores
- `AIResponse` - resposta estruturada das ações de assistência
- `AISuggestionItem` / `AIChecklistItem` - itens de sugestão e checklist
- `JEVSectionResult`, `JEVReportResult`, `JEVValidationResult` - resultados JEV
- `JEVExplanation` - explicações de critérios JEV
- `ProviderResponse` - resposta unificada dos provedores

## Configuração centralizada (Fase 3)

Todas as constantes mágicas foram extraídas para `app/config.py`:
- Limites de campos, contagens máximas, timeouts
- Endpoints de API, limites de tokens
- Níveis de score JEV, faixas de nota
- Configuração de rate limiting (`RATE_LIMITS`, `RATE_LIMIT_WINDOW_SECONDS`)
- Headers de segurança, constantes OAuth
- Limites de planos, catálogo jurídico
- Retenção de revisões, exclusão de conta, paginação

## Modelos públicos

A vitrine usa `app/domain/public-models.json`, extraído do conteúdo preenchido e anonimizado do legado. `static/js/app.js` apresenta dois modos distintos: o modelo preenchido mostra metadados e prévias por etapa; o documento completo mostra todas as seções, citações e referências disponíveis. Não reduzir o catálogo a placeholders.
