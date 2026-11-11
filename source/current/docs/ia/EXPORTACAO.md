# Revisão e exportação

## Prévia HTML

A rota autenticada de prévia reúne o snapshot salvo do projeto: identificação, descrição, decisões, critérios e fontes vinculadas à conta. O conteúdo é escapado antes de entrar no HTML. A prévia não lê o banco legado nem informações de outras contas.

A prévia é uma revisão, não uma confirmação de qualidade acadêmica. O usuário precisa conferir citações, formatação, completude e adequação à atividade.

## PDF Typst/ABNT

O PDF é produzido por um adaptador para Quarto que reutiliza a extensão ABNT Typst do produto de referência. O compositor original, os templates `typst-template.typ`, `typst-show.typ` e os tipos de documento `caso.typ`, `projeto.typ` e `artigo.typ` ficam versionados em `_extensions/abnt/`; a aplicação apenas mapeia o payload atual para esse contrato.

A renderização ocorre em diretório temporário, com o QMD e a extensão copiados para um workspace isolado. O texto do usuário entra como literal escapado; não pode introduzir comandos Typst ou Markdown executável. O diretório temporário é descartado ao final e o PDF só é devolvido quando o renderizador produz bytes PDF válidos.

O PDF do Case corresponde à fase Relatório, como no produto de referência. Debate e Dissertação continuam disponíveis na prévia HTML, mas não exibem um botão de PDF que o backend não consegue atender. Projeto de Paper e Paper Final usam seus tipos Typst específicos.

## Segurança e operação

A exportação exige sessão e propriedade do projeto. Fontes são filtradas pelos IDs pertencentes à conta antes de entrar no documento. O nome do arquivo é fixo e não é derivado de entrada do usuário.

Exportar não marca entrega, não compartilha o projeto, não envia conteúdo a provedor externo e não depende de WhatsApp. Uma falha do Quarto/Typst retorna indisponibilidade explícita; nunca devolve HTML com `application/pdf` falso.
