# Estado operacional do Assistente Acadêmico

A aplicação principal é independente em Python 3.13, Flask, Jinja, SQLite WAL, JavaScript local e Quarto. O banco é criado pelo schema próprio; nenhum dado do banco legado é importado ou consultado.

## Percursos disponíveis

- vitrine pública e healthcheck;
- Google OAuth com state, nonce, PKCE e verificação de claims;
- conta, perfil, termos e consentimento de IA separado;
- Case com identificação, fatos estruturados, decisões, critérios, debate e dissertação;
- Projeto de Paper e Paper Final com campos e progresso próprios;
- Biblioteca Pessoal com fontes isoladas por conta e vínculo a projeto/fato;
- autosave com revisão otimista e conflito explícito;
- agenda com prazos e tarefas;
- prévia HTML e PDF via Quarto com a extensão ABNT Typst do produto de referência;
- assistência contextual dentro das etapas, com revisão por campo, conversa/proposta, sugestões de pergunta-problema, teses, critérios, referências e checklist;
- avaliação JEV/Typesafe por etapa e relatório do Case, com probabilidades, faixa de pontos orientativa e explicação individual das observações;
- adaptadores DeepSeek, Gemini fallback e JEV/Typesafe testáveis sem rede;
- demonstrações públicas completas de Case, Projeto de Paper e Paper Final carregadas do catálogo estático anonimizado do legado;
- pesquisa jurídica contextual no editor, separada em Lei, Jurisprudência e Doutrina, usando o catálogo externo;
- fallback técnico Gemini implementado para as ações de assistência, aguardando somente a configuração opcional da chave;
- compartilhamento administrativo revogável e comentários fora do texto.

A Biblioteca Pessoal está limitada a fontes e fichamentos privados. O catálogo jurídico permanece disponível somente como insumo interno da pesquisa contextual, que usa o provedor principal e fallback técnico elegível sem expor nomes na interface. Google Scholar continua fora do produto; não há scraping nem chave Scholar configurada.

## Operação atual

O domínio `https://trab.sivaldodavi.com.br` aponta para o container `site-assistente-academico`, construído de `/opt/servidor/sites/assistente-academico/`. O banco principal fica em `/opt/servidor/data/assistente-academico/assistente_v2.sqlite3` e não compartilha dados com o legado.

O código e o banco anteriores foram preservados em `/opt/servidor/sites/assistente-academico-legado/` e `/opt/servidor/data/assistente-academico-legado/`. O legado possui Compose e bare repository próprios para consulta ou recuperação controlada, mas não atende o domínio principal.

O bare repository principal é `/home/git/repos/assistente-academico.git`; o legado é `/home/git/repos/assistente-academico-legado.git`. O checkout `/opt/servidor/work/assistente-academico/` é uma cópia de trabalho opcional. A publicação usa `/opt/servidor/deploy-site assistente-academico main`, que extrai a referência do bare repository para o diretório de sites.

O monitor técnico registra somente indicadores locais de site, container, banco e disco. O contato manual de atendimento fica fora da aplicação. Quarto 1.10.19 e a cadeia Typst/ABNT fazem parte da imagem/documentação de exportação.

O backup diário do banco é executado por `assistente-db-backup.timer`. A rotina versionada em `ops/assistente-db-backup` faz cópia consistente do SQLite, valida a integridade da cópia, testa uma restauração temporária e mantém arquivos por 14 dias. O procedimento operacional está em `docs/ia/OPERACAO-BACKUP.md`.

## Regras que não mudam

Pagamentos automáticos continuam fora do escopo. Nenhum dado do legado é importado automaticamente. O monitor técnico não envia mensagens e não depende de gateway. Nenhuma IA altera campos sem ação manual. Nenhum administrador é criado automaticamente; a lista é configuração externa. As regras acadêmicas pendentes significam somente campos, conferências e transições completas de Debate, Dissertação e Paper; não significam exportação de dados da conta.
