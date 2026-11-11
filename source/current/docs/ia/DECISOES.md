# Decisões da aplicação

## Aplicação independente

O banco de contas e projetos é próprio. Não importar identidades ou conteúdo do banco legado nem criar aliases de contas antigas. O projeto preservado é referência funcional, não backend da aplicação nova.

## Aparência e experiência preservadas

A mudança de stack não autoriza redesenho. Preservar campos, títulos, etapas, fases, dimensões e interações do produto de referência. Um editor de uma etapa por vez não pode ser substituído por uma página longa. Alterações de experiência que não sejam correções exigem autorização específica.

## Descrição dos fatos, sem cronologia

A narrativa dos fatos é redigida na etapa Descrição do caso. Não há Linha do Tempo/Cronologia dos Fatos. Não criar tabelas, payloads, controles ou exportações para esse recurso. A sua ausência é uma regra explícita do produto, não uma tarefa pendente.

## Integrações externas

Google OAuth, DeepSeek, JEV e Quarto ficam atrás de adaptadores pequenos e testes falsos. O gateway WhatsApp não é uma dependência da aplicação; o contato manual da vitrine é externo. O catálogo remissivo é um arquivo externo somente leitura; não compartilhar banco de usuários com o legado. Credenciais não entram em Git, frontend ou logs.

## Pagamentos manuais

Pix e atribuição de planos/créditos permanecem manuais. Não implementar gateway nem pagamentos automáticos.

## Autenticação e privacidade

Google OAuth verifica state, nonce, PKCE e claims. Administração é definida por e-mails configurados. Conta bloqueada não pode iniciar nem continuar acesso autenticado. Ser administrador não concede leitura de projetos sem compartilhamento autorizado; comentários permanecem separados da redação.

## Perfil e autorizações distintas

Perfil editável, aceite de termos e autorização de IA são dados separados. Salvar nome ou listas de disciplinas não altera consentimentos por ausência de campos. Consentimento de IA pode ser retirado sem retirar os termos gerais. O contato manual externo não é armazenado nem integrado ao Assistente.

## Ciclo de vida do projeto

O proprietário pode criar e excluir um projeto. A exclusão exige sessão, CSRF e confirmação explícita no navegador; remove o projeto e seus comentários/compartilhamentos em uma transação e não pode ser desfeita pela aplicação. Não há histórico, diff ou restauração de versões acadêmicas. A revisão interna existe apenas para impedir que autosave concorrente sobrescreva dados novos.

## Timeouts de IA configuráveis (Fase 2)

Os timeouts dos provedores de IA são configuráveis via variáveis de ambiente e não mais hardcoded. Isso permite ajustar para diferentes condições de rede e latência dos provedores externos sem alterar código.

Variáveis suportadas:
- `PROVIDER_TIMEOUT` (30s) - base
- `DEEPSEEK_TIMEOUT` (30s)
- `GEMINI_TIMEOUT` (30s)
- `JEV_TIMEOUT` (60s) - JEV costuma demorar mais

## AbortController no frontend (Fase 2)

Requisições de IA no frontend suportam cancelamento via `AbortController`:
- Apenas uma requisição ativa por vez (novas cancelam a anterior)
- Indicador visual de loading com spinner CSS
- Tratamento gracioso de `AbortError` (não mostra erro ao usuário)

## Design System Visual - Correções (Fase 4, Outubro 2026)

Decisão: corrigir inconsistências visuais críticas reportadas em produção sem redesenhar a aplicação, mantendo a paridade funcional.

### Problemas resolvidos
1. **Fontes minúsculas** (13px base): escala aumentada para md 15px + clamp fluido
2. **Contraste insuficiente dark mode**: muted #c0c0c0, dim #909090 (WCAG AA)
3. **Spacing gaps**: preenchidos space-13 a space-30
4. **Focus ring invisível**: 3px/4px offset
5. **Dropdown cortado por modal**: z-dropdown 55 > z-modal 50
6. **Select nativo quebrado**: reset completo com seta SVG customizada
7. **Botões inconsistentes**: 5 variantes padronizadas (.btn*)
8. **Empty states sem padrão**: componente unificado
9. **Timeline sem conectores**: pseudo-element vertical
10. **Mockups ilegíveis**: tipografia, tags, overflow controlados

### Limpeza de redundâncias (templates)
- Menu topbar duplicado → mantido apenas abas
- Botão "Sair" duplicado (header + footer) → apenas header
- Textos descritivos repetidos removidos
- "Organização" + "Agenda" unificados
- Pricing cards: "Projetos: X", "Assinatura" removidos
- WhatsApp isolado → integrado ao footer
- Mockup/abas/botões duplicados → mockup limpo + botões fora
- "Autorrespondidas" typo corrigido/removido

### O que NÃO mudou
- Estrutura de rotas, campos, etapas, workflows
- Paridade funcional com produto de referência
- Roteiros acadêmicos (case/paper), navegação por etapa
- Banco, autenticação, provedores IA, exportação PDF/Typst
- Limpeza automática em `beforeunload`

## Contratos TypedDict (Fase 3)

Todos os modelos de dados da aplicação agora usam `TypedDict` em `app/domain/types.py`:
- Tipagem estática para contratos entre camadas
- Facilita manutenção e refactoring
- Documentação viva dos schemas de dados

## Configuração centralizada (Fase 3)

Todas as constantes mágicas extraídas para `app/config.py`:
- Elimina números e strings mágicas espalhados
- Facilita ajustes operacionais
- Fonte única de verdade para limites, timeouts, headers
