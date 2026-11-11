# Comparação permanente com o legado

Este documento explica o que a aplicação principal preserva do produto de referência e quais diferenças ainda existem. Ele não é um diário de commits nem uma lista de tarefas temporária. Para regras visuais, consulte `PARIDADE-FUNCIONAL-ATUAL.md`; para o backup, consulte `OPERACAO-BACKUP.md`; para IA e avaliação, consulte `IA-EDITOR-JEV.md`.

## O que foi preservado

A aplicação principal mantém a vitrine pública, login Google, conta, perfil, termos, consentimento separado de assistência, Case, Projeto de Paper, Paper Final, Biblioteca Pessoal, fontes, fichamentos, agenda local, autosave, exclusão de projeto, compartilhamento revogável, comentários separados, revisão/entrega, assistência contextual, avaliação por etapa, pesquisa jurídica por Lei/Jurisprudência/Doutrina e exportação HTML/PDF com Typst/ABNT portado do legado.

Os três modelos públicos são conteúdos preenchidos e navegáveis em modo somente leitura. Cada modelo usa seu roteiro próprio: Case, Projeto de Paper ou Paper Final. A Biblioteca Pessoal mostra somente fontes e fichamentos da conta; o catálogo jurídico é um insumo interno da assistência e não uma tela de índice para a pessoa usuária.

## Decisões explícitas de produto

A aplicação não possui cronologia dos fatos, Linha do Tempo, histórico de versões, diff ou restauração de trabalhos. Backup operacional existe apenas para proteger o banco em caso de falha; não é um recurso de versões visível na conta.

Não há pagamento automático, importação de contas/projetos do banco legado, integração automática de mensagens ou dependência do gateway de mensagens. O contato manual de atendimento/Pix, quando exibido, é somente um link externo.

Paper Final não é uma terceira opção inicial independente: ele é alcançado pela transição do Projeto de Paper. A administração de planos e créditos é manual, sem checkout automático.

## Diferenças que ainda são reais

A equivalência acadêmica ainda não é total em quatro pontos. Primeiro, fontes ainda não possuem todos os vínculos finos do legado entre trecho, citação, tese, critério e localizador. Segundo, Debate e Dissertação ainda precisam das conferências e transições completas do fluxo de referência. Terceiro, Paper ainda precisa reproduzir integralmente todas as exigências, estados de entrega e regras de transição do legado. Quarto, a sessão ainda pode receber endurecimentos operacionais de expiração, revogação e política de origem.

“Conferências e transições completas” significa algo simples: quando uma pessoa termina uma etapa, o sistema deve verificar os mesmos campos e requisitos que o fluxo de referência verificava; ao passar de uma fase para outra, deve preservar o que precisa ser preservado e bloquear somente o que realmente falta. Isso não significa criar uma nova tecnologia, nem exportar dados da conta, nem inventar uma tela adicional.

A administração também pode ganhar indicadores operacionais mais amplos e o deploy pode receber troca atômica com rollback ensaiado. Essas são melhorias de operação, não funcionalidades que precisam aparecer para o usuário comum.

## Operação protegida

O banco principal é independente do legado. O backup diário usa `/usr/local/sbin/assistente-db-backup`, o timer `assistente-db-backup.timer`, integridade SQLite, restauração temporária de teste e retenção de 14 dias. O código versionado correspondente está em `ops/assistente-db-backup` e `services/assistente-db-backup.*`.

O monitor técnico registra saúde local no journal e não envia mensagens. O catálogo jurídico é montado separadamente em modo somente leitura. Secrets, banco, catálogo e dados de conta não entram no Git.

## Regra para futuras alterações

Uma diferença só deve ser corrigida depois de comparar template, CSS, JavaScript, rota, persistência e experiência de navegador com o legado correspondente. Se a diferença for uma decisão explícita desta aplicação, documentá-la como decisão de produto. Se for uma lacuna real, descrevê-la com o comportamento que falta; não esconder a lacuna trocando apenas o texto da interface.
