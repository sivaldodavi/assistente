# Matriz de equivalência funcional

Esta matriz define o produto que a aplicação deve preservar, independentemente da stack. A referência é o repositório `assistente-academico-legado`. Uma tela existir não comprova que seu fluxo completo ou seus documentos equivalem ao sistema anterior. Diferenças verificáveis ficam em `PENDENCIAS.md`.

| Área | Contrato de experiência |
| --- | --- |
| Vitrine | Navegação e exemplos funcionais; mesma identidade visual, preços e contratação manual |
| Google | Entrada e saída com validação segura; sem promoção automática a administrador |
| Primeiro acesso | Termos visíveis e IA separada; o site não coleta telefone nem envia mensagens automáticas |
| Perfil | Nome, cidade, instituição, curso, listas de disciplinas/professores; contexto de trabalhos novos, sem alterar os já criados |
| Navegação interna | Meus trabalhos, Biblioteca Pessoal, Meu perfil e Administração quando autorizada |
| Criação | Case, Projeto de Paper e Paper Final com os contratos de créditos, identidade e planejamento do produto |
| Editor | Um painel por etapa, Anterior/Continuar, sidebar no desktop e navegação horizontal no celular; textos, grupos, campos e conferências do roteiro original |
| Case | Relatório, Debate e Dissertação; argumentações das teses A/B em etapas próprias; critérios, referências e revisão |
| Paper | Planejamento e Paper Final no mesmo trabalho, com pesquisa original preservada e sem inventar conteúdo |
| Fatos | Narrativa na Descrição do caso; não existe cronologia de fatos |
| Autosave | Estado salvo/pendente/erro/conflito explícito, revisão otimista e preservação do texto local |
| Biblioteca | Cadastro, edição, exclusão, fichamentos pessoais, busca e reutilização das referências |
| Pesquisa jurídica | Catálogo externo somente leitura, usado internamente pela fundamentação assistida; não há tela de índice na Biblioteca |
| Fontes e fundamentação | Referências, critérios, definição/fundamento, teses, citações e fontes por argumento segundo o contrato de referência |
| Agenda | Prazos pertinentes ao tipo do trabalho e tarefas locais; não há lembretes automáticos |
| Projetos | Criar, abrir e excluir pelo proprietário; exclusão confirmada, com CSRF e sem restauração |
| IA/JEV | Ações especializadas, contexto permitido, consentimento, validação de resultados e ausência de aplicação automática |
| Uso | Créditos, limites, reservas, devoluções e acompanhamento sem contagem duplicada |
| Documentos | Composição acadêmica completa e modelos do produto, não apenas geração de qualquer PDF |
| Administração | Planos/créditos manuais, bloqueio, metadados e conteúdo somente quando compartilhado |
| Comentários | Fora da redação acadêmica e vinculados ao contexto/revisão pertinente |
| Atendimento manual | A vitrine mantém contato externo para dúvidas e comprovante Pix; não há integração automática |
| Operação | Deploy Python, secrets externos, backup íntegro, monitor no journal e recuperação pelo legado separado |

## Regra de verificação

Conferir o contrato automatizado, um erro relevante e a experiência em navegador real, incluindo desktop e celular. Comparar também as saídas e permissões, não apenas títulos de telas. Não substituir a funcionalidade ausente por texto anunciando uma versão menor; a reescrita não é autorização para reduzir o produto.
