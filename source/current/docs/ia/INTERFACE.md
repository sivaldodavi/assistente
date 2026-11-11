# Interface e navegação

## Fonte de verdade

A reescrita muda a implementação, não o produto visível. A referência de campos, textos, roteiros e dimensões é o Assistente Acadêmico preservado no repositório `assistente-academico-legado`. Simplificar código não autoriza apagar funcionalidades, reorganizar o percurso do usuário ou inventar novos recursos. Uma diferença relevante deve ser descrita e submetida ao titular, nunca escondida em documentação ou chamada de paridade.

Os roteiros acadêmicos originais estão transcritos em `app/domain/academic-workflows.json`, sem dependência de código executável do legado. Esse arquivo concentra títulos, instruções, campos, opções, grupos e conferências. Python controla persistência e composição; Jinja controla marcação; JavaScript controla a etapa visível.

## Identidade visual

Cores e controles base ficam em `static/css/app.css`. A vitrine usa `marketing.css`; módulos internos usam seus arquivos específicos. O editor usa as dimensões originais: sidebar de 190 px, intervalo de 24 px, cartão com 28 px de padding, título da etapa de 22 px e campos de 13 px. Não aumentar a tipografia e os espaçamentos para compensar uma arquitetura diferente. Perfil e biblioteca usam cabeçalho compacto e controles de 13 px.

Preservar o menu superior com Meus trabalhos, Biblioteca Pessoal, Meu perfil e Administração. Administração aparece somente para e-mails configurados, sem conceder privilégio automaticamente ao primeiro usuário. Links de navegação não devem depender de uma variável de template existir apenas em algumas páginas.

## Editor de Case e Paper

Há um único painel de edição visível por vez, com sidebar no desktop e navegação horizontal no celular. Anterior e Continuar trocam a etapa; a URL conserva a etapa aberta. A navegação não leva o usuário a uma página longa com todos os campos nem a uma coleção de acordeões acadêmicos. Somente ferramentas auxiliares, como planejamento e compartilhamento, são recolhíveis.

O Case mantém Relatório, Debate e Dissertação como fases reconhecíveis. As argumentações das teses A e B possuem etapas próprias. A Dissertação reúne introdução, desenvolvimento/fundamentação e conclusão em uma etapa de escrita; a revisão e entrega ficam em uma etapa separada. O desenvolvimento da dissertação e do Paper é organizado em tópicos editáveis.

Na revisão do relatório, a aplicação mostra as conferências agrupadas por etapa, a trilha manual de fundamentação, a avaliação orientativa, a prévia, o PDF Typst e a marcação de entrega. Essa marcação é apenas acompanhamento e continua permitindo edição. Os controles de assistência aparecem como um ícone discreto no canto superior direito do próprio campo de preenchimento; não colocá-los na linha do rótulo nem em um painel grande separado.

Projeto de Paper e Paper Final podem ser consultados no mesmo trabalho: a troca preserva identidade, planejamento e fontes, sem transformar hipóteses em conclusões ou gerar texto acadêmico por conta própria.

A narrativa pertence à Descrição do caso. **Não existe Linha do Tempo/Cronologia dos Fatos na aplicação.** Não reintroduzir esse recurso no editor, payload, testes positivos, exportação ou documentação de domínio.

## Perfil e biblioteca

Perfil alterna Dados pessoais e Termos e IA, sem exigir leitura de uma página enorme. Nome, cidade, instituição, curso, listas de disciplinas e professores preenchem o contexto de trabalhos novos. Alterar o perfil não modifica os trabalhos existentes. Termos são necessários para criar; IA é opcional e independente. O site não coleta telefone nem envia mensagens automáticas; o contato manual de Pix/suporte fica somente na vitrine.

A Biblioteca mostra somente Suas fontes. Cadastro e fichamento são recolhíveis; fontes podem ser editadas e excluídas apenas pelo proprietário. O editor também permite adicionar uma fonte e um fichamento opcional diretamente na etapa de referências, sem obrigar a abrir a Biblioteca. O catálogo jurídico é um volume externo somente leitura, sem dados de contas, usado internamente pelas sugestões de fundamentação. Fichamentos não entram automaticamente no PDF nem na assistência.

## Salvamento e verificação

Todos os campos do roteiro permanecem no mesmo formulário, mesmo quando sua etapa está escondida. Trocar etapas não elimina conteúdo do autosave. Requisições são serializadas por revisão técnica; novas alterações durante uma resposta são salvas depois. Conflito não sobrescreve os dados salvos. Exportação e troca do modo Paper aguardam salvamento bem-sucedido. Formulário acadêmico e compartilhamento nunca podem ser aninhados. Na lista de trabalhos, o proprietário pode excluir um projeto; exclusão exige confirmação e não oferece restauração.

O teste opcional `python3 tests/browser/check_workflow.py` usa Chromium, banco temporário e conta fictícia. Deve verificar um painel por vez, conteúdo preservado ao navegar, autosave, conferências, fases, Paper, perfil, biblioteca, links e largura em desktop/celular. Testes não chamam Google, DeepSeek, JEV ou zap-go reais.

A recuperação de interface não comprova equivalência total de documentos ou IA. Revisar especificamente composição acadêmica/ABNT do PDF, fontes por citação, regras completas de uso e todos os assistentes especializados antes de anunciar paridade integral. Histórico, diff e restauração de versões não fazem parte do produto.
