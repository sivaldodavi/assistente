# Catálogo jurídico

O catálogo jurídico é um SQLite externo, somente leitura para a aplicação web. Ele não pertence ao banco de contas e projetos e não contém identidades, sessões ou conteúdo privado.

## Bases

O catálogo reúne três tipos canônicos:

- `legislation`: Índice alfabético-remissivo do Vade Mecum Método, 16ª edição de 2023. É uma remissão de termo, norma e referência; não é o texto integral da lei.
- `book`: metadados jurídicos do acervo da Plataforma Minha Biblioteca/UFOB de 2021. O registro é uma pista bibliográfica; não concede acesso ao livro.
- `case-law`: metadados e ementas oficiais dos espelhos da Quarta Turma do STJ. Ementa não é inteiro teor nem decisão completa.

A interface diferencia a Biblioteca Pessoal desse catálogo. A Biblioteca guarda referências escolhidas pelo usuário; o catálogo é o acervo externo usado para pesquisa e sugestões contextualizadas.

## Arquivos e importadores

Os importadores portados do produto de referência ficam em `scripts/`:

- `import_epub_index.py` — Vade 2023;
- `import_ufob_csv.py` — livros jurídicos 2021;
- `import_stj_metadata.py` — ementas STJ;
- `research_catalog.py` — normalização, IDs estáveis, deduplicação, FTS5 e escrita atômica.

Eles geram o catálogo em um diretório de trabalho e não abrem o banco de usuários. O processo de atualização deve gerar um novo arquivo, validar contagens/metadados e substituir o SQLite de forma atômica. Uma falha de importação não pode deixar o catálogo atual pela metade.

## Produção

No VPS, o volume atual fica em `/opt/servidor/data/assistente-academico/catalogs/` e é montado como `/catalogs:ro`. A aplicação recebe `RESEARCH_CATALOG_PATH=/catalogs/catalog.sqlite3`. O catálogo não deve ser colocado dentro do volume gravável do banco principal nem compartilhado com o banco legado.

A consulta simples não chama IA. A recomendação contextual só ocorre por ação explícita do usuário e recebe candidatos reconsultados pelo servidor. O navegador envia IDs, mas título, tipo, origem, ano, referência e ementa são sempre lidos novamente do catálogo.

## Sugestões e proveniência

A recomendação divide os resultados em Lei, Jurisprudência e Doutrina. Cada item conserva `source_id`, tipo, título, referência, autor, ano, origem e justificativa curta. A IA não pode inventar um identificador ou uma fonte fora dos candidatos fornecidos.

Adicionar uma sugestão à Biblioteca Pessoal é uma ação explícita. O sistema copia somente os metadados disponíveis, registra que a origem foi o catálogo e deixa a conferência dos dados e da pertinência sob responsabilidade do usuário.

## Atualização externa

Google Scholar não é raspado pela aplicação. Uma integração de terceiro, se autorizada no futuro, ficará em adaptador separado, opcional, com chave, limite, cache e marcação de resultado externo. Ela não substitui os três corpora jurídicos locais.
