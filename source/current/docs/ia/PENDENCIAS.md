# Pendências de equivalência e operação

Este arquivo reúne diferenças verificáveis entre a aplicação Python e o produto de referência, sem tratar uma recuperação parcial de interface como paridade integral. As regras permanentes da interface ficam em `INTERFACE.md`; o roteiro de referência fica em `app/domain/academic-workflows.json`.

## Paridade funcional a conferir

- Composição acadêmica completa/ABNT, modelos e materiais de apoio do PDF. A cadeia Quarto/Typst agora reutiliza a extensão do produto de referência; ainda falta validar visualmente todos os modelos em produção.
- Regras de uso: reservas, limites efetivos na criação, concessão por plano, uso de IA por trabalho, falhas/devoluções e exibição de saldo. O painel de concessão manual e os contadores não substituem essas regras.
- A pesquisa contextual consulta Vade 2023, livros jurídicos 2021 e ementas STJ, usa pergunta-problema/instruções/palavras-chave, separa Lei/Jurisprudência/Doutrina e permite adicionar uma sugestão confirmada à Biblioteca. Os assistentes especializados do legado, a revisão por campo, as sugestões de teses/critério/referências, as checklists e a avaliação JEV do Case estão disponíveis dentro das etapas. A busca institucional separada continua fora do percurso local.
- Estados de entrega por fase e comentários vinculados ao contexto acadêmico; a aplicação não manterá histórico de versões.
- Citações vinculadas a trechos/argumentações e importação automática de resultados para referências. O fallback Gemini já existe no código e está configurado como secret vazio no VPS; a chave só precisa ser preenchida se você quiser habilitá-lo.

Não retirar essas diferenças da lista apenas porque uma tela equivalente existe. Resolver usando o legado como referência de contrato e experiência, sem compartilhar banco de contas nem executar o backend antigo como parte da aplicação nova.

## Verificação operacional

Conferir restart, healthcheck e logs sem conteúdo privado. O backup diário do banco já está ativo em `assistente-db-backup.timer`: ele usa cópia consistente do SQLite, executa integridade, restaura uma cópia temporária para validação e retém 14 dias. O procedimento de recuperação está em `docs/ia/OPERACAO-BACKUP.md`. O catálogo de pesquisa deve permanecer somente leitura, separado do banco de contas. O monitor técnico registra no journal e não depende de mensagens.

O teste de navegador com banco temporário verifica etapas, fases, autosave, perfil, Biblioteca Pessoal sem índice público e responsividade. OAuth real deve ser observado somente durante uso autorizado normal; o contato manual externo não é chamado em testes.

## Fora do escopo autorizado

Não implementar pagamento automático, importar contas/projetos antigos, juntar bancos ou trocar provedores/credenciais. O atendimento manual da vitrine é externo; não criar integração automática de mensagens. Não reintroduzir cronologia de fatos.
