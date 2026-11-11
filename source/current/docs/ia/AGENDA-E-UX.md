# Agenda e experiência de organização

## Objetivo

A agenda organiza as datas e tarefas de cada trabalho sem criar um sistema de notificações. Ela precisa ser encontrada naturalmente na conta, continuar disponível dentro do editor e refletir o roteiro real de Case, Projeto de Paper e Paper Final.

A referência de comportamento é o módulo de agenda preservado no legado. A implementação nova usa Flask/Jinja, SQLite e JavaScript modular, sem importar o banco ou executar o backend antigo.

## Diagnóstico de paridade

Na comparação com o legado, o bloco recolhível de planejamento do editor não bastava para compor uma agenda utilizável. A auditoria identificou estas diferenças que orientaram a implementação:

- não havia calendário nem resumo de próximas entregas na conta;
- o planejamento de Paper mostrava somente Paper Final e escondia a data do Projeto de Paper;
- tarefas não tinham marcação de concluída;
- não havia o botão para inserir o roteiro sugerido de tarefas;
- o domínio descartava `done`, etapa e identificação do roteiro ao normalizar tarefas;
- a conta recebia somente título/tipo/revisão dos projetos, sem datas para montar uma agenda;
- o JavaScript do editor acumulava autosave, navegação, assistência, pesquisa jurídica e planejamento no mesmo arquivo.

Essas diferenças são de UX e funcionamento percebido, não apenas de nomenclatura. O estado vigente abaixo resolve esse conjunto sem reintroduzir os serviços removidos.

## Estado funcional vigente

A conta mostra o calendário e o editor mantém o planejamento recolhível no topo, com os campos e estados descritos a seguir.

## Contrato da agenda

Cada projeto mantém no próprio payload:

- `report_date`: entrega do relatório do Case ou entrega do Projeto de Paper;
- `debate_date`: data do debate do Case;
- `dissertation_date`: entrega da dissertação do Case;
- `final_date`: entrega do Paper Final;
- `tasks`: até 100 tarefas com `id`, `title`, `date`, `done`, `stage` e `template_key`.

A aplicação aceita datas ISO (`AAAA-MM-DD`) e a forma legada brasileira (`DD/MM/AAAA`) somente para normalização. Datas inválidas são descartadas. Título de tarefa é limitado no servidor; tarefas sem título ou sem data continuam editáveis no planejamento, mas não entram no calendário de entregas da conta.

Para Paper, `report_date` representa o Projeto de Paper e `final_date` representa o Paper Final. A transição entre os dois modos conserva ambas as datas e as tarefas.

A agenda não envia e-mail, WhatsApp ou qualquer outra mensagem. Ela não marca automaticamente uma fase como entregue, não altera campos acadêmicos e não chama IA.

## Experiência da conta

A conta autenticada mostra uma seção compacta **Agenda** próxima das ações de criação e dos trabalhos:

- calendário mensal do mês atual, com no máximo duas entradas visíveis por dia;
- lista de próximas datas, limitada às cinco mais próximas;
- quando não há datas, a seção não desenha uma grade vazia e explica onde cadastrar o planejamento;
- quando existem datas, mas nenhuma pertence ao mês atual, a seção informa isso e mantém somente a lista de próximas datas, sem uma grade vazia;
- cada entrada abre diretamente o projeto correspondente;
- Paper mostra separadamente Projeto de Paper e Paper Final;
- o mapa de calor usa a quantidade de salvamentos do dia, não a quantidade de datas planejadas;
- quando todas as datas são passadas, a lista mostra as datas cadastradas mais recentes, em vez de desaparecer.

A agenda não substitui a lista de trabalhos. A lista continua sendo o lugar para continuar ou excluir um trabalho.

O cadastro de fonte não exige abrir a Biblioteca: na etapa de referências, **Adicionar fonte** cria a fonte e o fichamento opcional no próprio editor. A Biblioteca continua sendo o lugar para administrar fontes fora de um trabalho.

## Experiência do editor

O bloco **Planejar este trabalho** permanece no topo, junto de compartilhamento e comentários, antes do roteiro acadêmico. Ele é recolhível para não competir com o campo que está sendo escrito, mas o resumo do cabeçalho informa se há datas e quantas tarefas estão concluídas.

Dentro dele:

- Case mostra entrega do relatório, debate e dissertação;
- Projeto de Paper e Paper Final mostram entrega do Projeto de Paper e do Paper Final;
- `Usar roteiro sugerido` adiciona as tarefas do roteiro sem repetir títulos ou chaves já existentes;
- `Adicionar tarefa` cria uma tarefa livre;
- cada tarefa tem checkbox de concluída, título, data e remoção;
- tarefas concluídas permanecem visíveis, com texto riscado e estado salvo;
- alterar título, data, checkbox ou prazo usa o mesmo autosave do editor;
- o texto explica que o planejamento é pessoal e pode ser alterado.

As tarefas sugeridas reproduzem os títulos do legado. Elas são auxílio de organização, não novos campos acadêmicos e não alteram o conteúdo do trabalho.

## Estrutura de implementação

- `app/domain/schedule.py` normaliza datas/tarefas, resolve aliases antigos, fornece os modelos sugeridos e transforma prazos do payload em entradas de calendário.
- `app/store/projects.py` acrescenta ao resumo da conta somente datas públicas e a contagem agregada de salvamentos do próprio proprietário; não lê conteúdo acadêmico para a agenda.
- `app/routes/projects.py` monta o calendário da conta e entrega os dados já ordenados ao template.
- `templates/account/home.html` renderiza o calendário server-side com links normais para os projetos.
- `templates/projects/editor.html` mantém somente a marcação do planejamento.
- `static/js/project-schedule.js` concentra coleta, tarefas sugeridas, checkbox, remoção e atualização do resumo; `project-editor.js` continua responsável por autosave e usa o módulo por uma interface pequena.
- `static/css/app.css` e `static/css/editor.css` reutilizam a densidade visual do legado, com grade compacta e comportamento responsivo.

Os arquivos `public-models.json` e `academic-workflows.json` são dados versionados, não monólitos de lógica. O maior arquivo de código do editor será reduzido pela extração do planejamento, sem criar uma camada genérica ou framework novo.

## Fora do escopo

Não implementar lembretes automáticos, workers, WhatsApp, e-mail, pagamento, cronologia dos fatos, histórico/diff/restauração de versões ou alteração automática do texto acadêmico. Backup operacional do banco permanece separado da agenda.

## Critério de funcionamento

A agenda só é considerada recuperada quando testes provarem, usando banco temporário, que:

1. Case exibe as três datas e o roteiro sugerido correto;
2. Projeto de Paper e Paper Final exibem as duas datas do mesmo trabalho;
3. concluir, editar, adicionar e remover tarefas permanece salvo após recarregar;
4. a conta mostra as datas no calendário e nas próximas entregas, com links para o projeto;
5. conta sem datas não apresenta calendário vazio;
6. desktop e celular não criam overflow horizontal;
7. nenhuma mensagem automática ou recurso explicitamente removido reaparece.
