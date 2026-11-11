# Agenda e organização

## Agenda

Cada projeto mantém no próprio snapshot quatro prazos (`report_date`, `debate_date`, `dissertation_date` e `final_date`) e até 100 tarefas com `id`, `title`, `date`, `done`, `stage` e `template_key`. Para Case, os prazos representam relatório, debate e dissertação. Para Paper, `report_date` representa o Projeto de Paper e `final_date` representa o Paper Final do mesmo trabalho.

Datas são aceitas em ISO (`AAAA-MM-DD`) e a forma legada brasileira (`DD/MM/AAAA`) é normalizada no servidor. Entradas inválidas são descartadas. Tarefas sugeridas são inseridas no editor sem repetir chaves ou títulos; tarefas livres podem ser concluídas, editadas e removidas.

A conta transforma os prazos do projeto em uma lista de próximas datas e mostra um calendário mensal combinado com atividade. Cada entrada abre o respectivo projeto. A intensidade do mapa de calor é a quantidade de salvamentos automáticos/manuais no dia, agregada por conta; não representa quantidade de prazos nem guarda versões ou conteúdo. A grade só aparece quando há prazo ou atividade no mês atual.

A agenda é organização do usuário: salvar uma data ou concluir uma tarefa não marca entrega, não chama IA e não envia e-mail ou WhatsApp. Não existem workers nem lembretes automáticos. O monitor técnico verifica apenas o site, container, banco e disco.

O planejamento aparece no topo do editor, junto de compartilhamento e comentários, em bloco recolhível. O módulo `static/js/project-schedule.js` coleta a agenda, insere o roteiro sugerido e atualiza o resumo; o autosave geral continua em `project-editor.js`.

O agregado `project_edit_days` guarda projeto, conta, dia e quantidade de salvamentos. Ele é descartado após 365 dias e serve somente à visualização da atividade; não é histórico de versões, diff ou restauração.
