# Biblioteca Pessoal

## Objetivo

A Biblioteca Pessoal guarda referências que pertencem à conta e podem ser reutilizadas em mais de um projeto. Ela não é uma lixeira de textos nem uma lista pública de obras.

## Registro de fonte

Uma fonte possui título obrigatório, autor/órgão opcional, tipo, referência bibliográfica ou link e fichamento pessoal privado. O tipo é controlado: livro, artigo, legislação, jurisprudência, site ou outro.

O fichamento é a anotação pessoal curta da fonte: ideia central, trecho a conferir ou forma como o material pode ajudar. Ele é armazenado no campo privado `sources.notes`, com limite de 5.000 caracteres, pode ser editado junto com os dados da fonte e não entra automaticamente em PDFs, citações ou solicitações de IA.

A fonte e o fichamento podem ser alterados ou excluídos somente pela conta proprietária. O servidor confere `account_id` na própria operação; um ID arbitrário não permite ler, alterar ou remover a fonte de outra conta.

## Catálogo jurídico interno

A tela da Biblioteca não oferece consulta ao índice alfabético-remissivo. O catálogo jurídico somente leitura continua separado do banco de usuários e é consultado internamente pela assistência contextual, que usa seus registros de legislação, jurisprudência e doutrina para montar sugestões. Ele não cria fontes pessoais automaticamente.

O arquivo é configurado por `RESEARCH_CATALOG_PATH`, normalmente `/catalogs/catalog.sqlite3` no container novo. O banco de contas da aplicação não é consultado. Se o arquivo não estiver montado, a Biblioteca Pessoal continua abrindo e o cadastro de fontes permanece funcional.

## Vínculo com projeto

As etapas acadêmicas guardam somente IDs de fontes. No servidor, cada ID é validado contra a conta proprietária antes de ser salvo. Um usuário não consegue vincular ou descobrir a fonte de outra conta enviando um ID arbitrário.

O editor apresenta fontes disponíveis em caixas de seleção. Não é necessário digitar UUID ou texto solto para criar um vínculo.

## Experiência visual

A Biblioteca mostra somente Suas fontes. O cadastro é recolhível e a lista usa divisórias. Título, autor/tipo e referência aparecem primeiro; o fichamento fica recolhido quando existe. A edição abre no próprio item, a exclusão pede confirmação e o layout funciona em uma coluna no celular usando os componentes do site.
