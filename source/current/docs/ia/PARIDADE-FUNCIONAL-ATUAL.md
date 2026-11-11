# Paridade funcional atual

Este documento é a referência permanente para comparar a experiência do Assistente com o produto de referência preservado no repositório legado. A comparação é feita pelo comportamento percebido pela pessoa usuária, não pela quantidade de arquivos ou pela linguagem usada.

## Correções que fazem parte do contrato atual

- A vitrine oferece três modelos preenchidos em modo somente leitura, navegáveis pelo roteiro correto de Case, Projeto de Paper e Paper Final. O conteúdo de cada seção é associado ao título canônico da etapa; os cabeçalhos vazios preservados no modelo legado não podem deslocar o texto para outra etapa. Os campos visíveis usam os valores do modelo anonimizado e, quando o roteiro novo separa um campo que antes estava agregado, somente trechos literais ou diretamente identificáveis do mesmo conteúdo são reutilizados.
- A conta sem plano exibe planos e valores em uma tela direta (`/planos`). O link não deve obrigar a pessoa a voltar à home e localizar manualmente a seção de preços. Pagamentos continuam manuais; não existe pagamento automático.
- A criação de projetos respeita créditos de projeto de forma atômica. A conta administrativa configurada não fica limitada; as demais contas são bloqueadas quando o saldo chega a zero. A duplicação usa a mesma regra.
- Paper Final é uma transição do Projeto de Paper pelo fluxo do próprio projeto. Não é uma terceira opção inicial no formulário da conta. Registros existentes desse tipo continuam legíveis.
- Compartilhamento e comentários ficam no topo do editor, próximos do planejamento, em formulário separado do autosave. A revogação de comentários impede que a administração continue vendo comentários depois da alteração.
- A assistência aparece de forma compacta e contextual. Resultados vazios não exibem barra vertical, reserva de altura ou cartão vazio. Nomes de provedores e detalhes internos não aparecem na interface.
- A revisão e entrega do relatório permanecem como etapa própria do Case. A narrativa dos fatos fica na descrição do caso; não existe cronologia dos fatos, histórico de versões ou restauração.
- A Biblioteca Pessoal contém fontes e fichamentos privados. O catálogo jurídico interno não é uma aba da Biblioteca: ele é usado apenas quando a pessoa pede fundamentação contextual no Case.
- A agenda fica disponível na conta e no topo recolhível do editor. Case mostra relatório, debate e dissertação; Paper mostra Projeto de Paper e Paper Final. Tarefas podem usar o roteiro sugerido, ser concluídas e permanecer salvas; a conta exibe prazos e um mapa de calor cuja intensidade é a quantidade de salvamentos por dia, sem enviar mensagens.
- A Dissertação do Case é uma etapa de escrita com introdução, desenvolvimento/fundamentação e conclusão, seguida por uma revisão e entrega própria. Referências não são uma etapa obrigatória separada; fontes podem ser adicionadas dentro do próprio editor.

## Funcionalidades implementadas nas Fases 1-3

### Fase 1: UX/Design System (Concluída)
- Sistema de design tokens centralizado (`static/css/tokens.css`) - cores, espaçamento, tipografia, bordas, sombras, transições
- CSS refatorado usando tokens em todos os 6 arquivos (app.css, editor.css, marketing.css, admin.css, library.css, profile.css)
- JavaScript modularizado em ES Modules:
  - `autosave.js` - Salvamento automático otimista
  - `project-schedule.js` - Editor de cronograma
  - `project-ai.js` - Assistência contextual rica
  - `pdf-export.js` - Exportação Quarto
  - `duplicate.js` - Duplicação de projetos
  - `revisions.js` - Histórico de revisões
  - `jev-panel.js` - Painel JEV (seção, relatório, explicação)

### Fase 2: Operational IA/PDF (Concluída)
- Timeouts configuráveis para todos os provedores (DeepSeek, Gemini, JEV) via variáveis de ambiente
- AbortController no frontend para cancelamento de requisições de IA
- Indicador visual de loading com spinner CSS animado
- Fallback gracioso DeepSeek → Gemini → JEV preservado
- Melhorias na UX de loading e feedback ao usuário

### Fase 3: Quality/Maintainability (Concluída)
- Contratos TypedDict em `app/domain/types.py` para todos os modelos de dados
- Configuração centralizada em `app/config.py` (elimina constantes mágicas)
- Rate limiting granular por ação preservado
- Security headers (CSP, HSTS, Permissions-Policy, COOP/COEP) preservados

### Fase 4: Visual Design System Fixes (Concluída - Outubro 2026)
- **Tokens & Tipografia** (`tokens.css`): base 13px→15px, clamp fluido body, contraste #c0c0c0/#909090, spacing gaps preenchidos, focus ring 3px/4px, z-dropdown 55>50, sidebar tokens, containers semânticos
- **Containers & Layout**: refs semânticas em 7 arquivos CSS, sidebar responsiva (1100/900/680px), pricing 2-col (~1000px), library grid fix
- **Componentes**: hardcoded #393939→token, select reset SVG, botões .btn* padronizados, empty-state, user-email, FAQ padding, timeline connector, mockup containers, footer spacing
- **Templates**: 13 redundâncias removidas (menu duplicado, sair duplicado, textos repetidos, WhatsApp isolado, mockup/buttons duplicados, typo "Autorrespondidas"), pricing simplificado, FAQ limpo

## Diferenças que ainda devem ser tratadas como lacunas

Estas capacidades não devem ser anunciadas como equivalentes sem implementação e teste específicos:

- vínculos acadêmicos completos entre fonte, citação, tese, critério e localizador;
- conferências e registros acadêmicos completos das fases de Debate e Dissertação;
- requisitos de Paper, entrega por fase e transição completa para Paper Final;
- expiração/revogação server-side da sessão, política de origem e testes de cookie/logout equivalentes ao legado;
- deploy atômico com rollback ensaiado. O backup do banco já possui rotina diária, validação de integridade, restauração temporária de teste e retenção de 14 dias; o procedimento está em `docs/ia/OPERACAO-BACKUP.md`.

Quando este documento fala em "conferências e registros acadêmicos completos", não está falando de uma tecnologia nova ou de um recurso misterioso. Significa apenas garantir que Debate, Dissertação e Paper tenham os mesmos campos obrigatórios, checklists, estados de entrega e transições que existiam no fluxo de referência. Isso é uma regra de funcionamento do trabalho acadêmico, não uma obrigação de exportar dados da conta.

## Fora do produto

Não reintroduzir cronologia dos fatos, histórico/diff/restauração de versões, pagamento automático ou integração automática de WhatsApp. O contato manual de suporte/Pix, quando exibido em página pública, é apenas um link externo e não cria dados, fila ou serviço no Assistente.

## Regra para novos agentes

Antes de alterar uma tela, comparar o template, o CSS, o JavaScript e o contrato do legado correspondente. Não criar um redesign por preferência própria quando a solicitação for de equivalência. Para cada diferença encontrada, classificar como correção necessária, decisão explícita de produto ou lacuna ainda não implementada; nunca esconder uma lacuna apenas mudando o rótulo da interface.
