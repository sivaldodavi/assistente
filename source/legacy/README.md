# Assistente Acadêmico

Projeto privado de uso e desenvolvimento interno. Aplicação web para organizar
relatórios de case jurídico, Projetos de Paper e Papers Finais, com salvamento
por conta, revisão guiada e exportação opcional em PDF.

## Como funciona

- O acesso é por código. Projetos são armazenados no serviço e podem ser
  retomados em outros dispositivos; salvamentos usam controle de revisão.
- Cada trabalho tem etapas, campos e checklist. O progresso organiza a revisão,
  mas não atesta a correção jurídica, a qualidade das fontes ou a conformidade
  com a orientação do professor.
- O Paper Final permite adicionar, remover e reordenar tópicos de
  desenvolvimento. Checklist pendente não impede marcar o trabalho como
  finalizado, gerar prévia ou exportar PDF.
- A conferência de citações e referências é heurística e local. Alertas pedem
  revisão humana e não certificam ABNT, existência ou correção das fontes.
- A exportação compila Typst no navegador. Os modelos acadêmicos são mantidos
  em repositório separado e não são importados automaticamente pelo app.

## Assistência por IA

As ações **Revisar este texto**, **Entender esta observação**, **Sugerir
preenchimento** e **Conversar sobre este trabalho** estão disponíveis nos
fluxos de case, Projeto de Paper e Paper Final. A proposta/instrução do
professor é necessária para a avaliação estruturada e para a assistência
contextual (revisão, checklist e conversa), mas não para salvar ou exportar o
projeto. A explicação opcional de uma observação da análise de case usa somente
o critério e os trechos pertinentes.

As revisões recebem o campo escolhido, a proposta e o contexto acadêmico do
projeto; identidade e lista cadastrada de referências não são incluídas. No
chat, o estudante pode desativar o envio dos outros textos, mantendo a proposta
como contexto obrigatório. Referências cadastradas podem ser revisadas uma por
vez, sob ação explícita. O chat é temporário no navegador; as mensagens não são
salvas no banco.

Uma revisão pode sugerir uma versão alternativa de um campo, mas só a substitui
se o estudante confirmar. O chat nunca altera o projeto diretamente. Ao pedir
sugestões da checklist, itens com evidência clara ficam pendentes de aceite
individual ou conjunto; nada é marcado sem essa ação. Escolhas manuais não são
sobrescritas, marcações aceitas podem ser alteradas ou desfeitas, e uma edição
posterior do texto sinaliza a avaliação como desatualizada. O limiar interno de
70% não é uma probabilidade calibrada nem prova de acerto. Itens que dependem de
verificação externa, ações do estudante ou formatação continuam sob conferência
humana.

A avaliação estruturada baseada na rubrica FACSUR permanece específica ao
relatório de case. A assistência contextual, revisão de texto, conversa e
sugestões de checklist abrangem os três fluxos. Revisões apresentam observação,
evidência do material enviado e até duas sugestões concretas. Nenhuma resposta
é nota oficial, validação jurídica ou conferência automática da autenticidade
de fontes. Sugestões são pontuais e não devem substituir a autoria do estudante.

Os nomes dos provedores e o detalhamento do tratamento de dados estão na página
interna de [ajuda sobre IA e privacidade](/ajuda-ia/). As cotas de análise
estruturada e assistência são separadas; a cota de assistência é compartilhada
entre revisões, conversas, sugestões e explicações. Falhas também consomem uma
chamada.

## Desenvolvimento local

Requisitos: Node.js/npm, Hugo e Python 3.13 ou compatível.

```sh
npm ci
npm run build
python3 -m unittest discover -s tests
```

Para executar o app e a API na mesma origem, use um diretório de dados
temporário:

```sh
ASSISTENTE_DATA_DIR=/tmp/assistente-academico \
ASSISTENTE_PUBLIC_DIR=public \
ASSISTENTE_COOKIE_SECURE=0 \
ASSISTENTE_PORT=8080 \
python3 server.py
```

Para chamadas locais, configure `TYPESAFE_API_KEY` e `DEEPSEEK_API_KEY` no
ambiente do processo. Nunca inclua chaves, códigos, textos de trabalhos ou
respostas de provedores no repositório, imagem, logs ou mensagens. A
documentação operacional é mantida separadamente em ambiente interno e não é
publicada com a aplicação.
