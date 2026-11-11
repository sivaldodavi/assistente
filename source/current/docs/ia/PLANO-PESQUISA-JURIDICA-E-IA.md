# Plano de pesquisa jurídica e sugestões por IA

## Decisão de produto

A Biblioteca Pessoal guarda fontes escolhidas pelo usuário. O catálogo jurídico é um acervo externo, separado do banco de contas, que fornece registros de legislação, jurisprudência e doutrina somente para a fundamentação assistida; ele não é uma seção da Biblioteca.

O percurso correto acontece dentro do trabalho, na etapa de fontes e pesquisa. O usuário informa a pergunta-problema, as instruções do professor e, quando necessário, palavras-chave. O sistema consulta primeiro o catálogo jurídico real. Depois, sob ação explícita do usuário, a IA sugere pistas separadas em três grupos: **Lei**, **Jurisprudência** e **Doutrina**.

A IA não escolhe uma autoridade “do nada”, não inventa número de processo, não transforma um livro em fonte cadastrada automaticamente e não apresenta uma recomendação como parecer jurídico. Ela recebe candidatos existentes no catálogo, devolve os identificadores desses candidatos e explica, em poucas linhas, por que cada um pode ser pertinente à pergunta. O usuário confere a fonte, edita o uso pretendido ou descarta a sugestão.

Esta é uma recuperação de comportamento do legado, não um redesign. O legado já contém a maior parte dos contratos necessários em `research_catalog.py`, `scripts/import_epub_index.py`, `scripts/import_ufob_csv.py`, `scripts/import_stj_metadata.py`, `web_search.py`, `ai_support.py`, `providers.py`, `store/usage.py` e `assets/js/main.js`. A nova aplicação deve portar esses contratos, não inventar uma biblioteca genérica novamente.

## O acervo que precisa existir

O catálogo deve continuar sendo um SQLite somente leitura, fora do banco de contas e projetos. A tabela pública mantém `id`, `kind`, `title`, `reference`, `author`, `abstract`, `source_year`, `source`, `search_text` e `payload`. Os únicos tipos canônicos são `legislation`, `case-law` e `book`; a entrada `case_law` pode ser aceita apenas como alias de compatibilidade no request.

O primeiro corpus é o índice alfabético-remissivo do Vade Mecum Método, 16ª edição de 2023. Ele não representa o texto integral das leis. Cada registro aponta para um termo, uma norma e uma remissão, com origem claramente identificada. A interface deve chamar isso de **Índice remissivo · 2023** e não prometer que o catálogo contém todos os dispositivos legais.

O segundo corpus é o acervo jurídico da plataforma Minha Biblioteca/UFOB de 2021. Ele oferece metadados de livros jurídicos, como título, autor, ISBN, ano e origem. Não oferece o conteúdo integral dos livros. A interface deve chamá-lo de **Livros jurídicos · 2021** e deixar claro que o resultado é uma pista bibliográfica para conferência.

O terceiro corpus é formado por metadados e ementas oficiais do STJ. O importador legado utiliza o pacote de dados abertos da Quarta Turma, preserva ementa, identificação do processo, órgão julgador, data e termos auxiliares, e deliberadamente não salva o campo de decisão ou o inteiro teor. A interface deve chamar isso de **Ementas STJ** e nunca apresentar ementa como se fosse acórdão completo.

Os três importadores do legado devem ser reutilizados ou portados quase literalmente, com testes de seus formatos atuais. A atualização do catálogo precisa ser determinística, gerar IDs estáveis, deduplicar registros e escrever o SQLite de maneira atômica. O banco de usuários não participa dessa atualização.

## Experiência do usuário

Na etapa de decisões/fundamentação do Case, o editor oferece a ação manual **Pedir sugestões para este trabalho**. Ela consulta candidatos do catálogo e usa o contexto do trabalho para separar Lei, Jurisprudência e Doutrina. Nunca deve ser disparada por autosave, por digitação ou ao abrir a tela. Cada etapa também oferece, no próprio contexto, revisão de campo, pergunta-problema, teses, critérios, referências, checklist e avaliação estruturada. O resultado é orientação confirmável, não preenchimento automático.

Antes da sugestão, o usuário deve poder revisar os campos enviados: pergunta-problema, instruções do professor, palavras-chave, título, teses, objeto de pesquisa, teoria e fontes selecionadas. O sistema deve indicar quando algum campo está vazio. Em particular, sem instruções do professor a IA pode oferecer somente uma pista geral; não pode afirmar que a sugestão atende à atividade.

O resultado deve aparecer em três blocos independentes:

- **Lei:** registros do tipo `legislation`.
- **Jurisprudência:** registros do tipo `case-law`, especialmente ementas e metadados do STJ.
- **Doutrina:** registros do tipo `book`.

Cada cartão mostra origem, ano, título, referência, autor quando houver, e uma justificativa curta da pertinência. Também mostra avisos de escopo: índice remissivo não é texto legal integral; ementa não é inteiro teor; livro catalogado não significa acesso ao conteúdo. As ações são **Aplicar**, **Editar antes** e **Descartar**. Aplicar não deve substituir texto acadêmico nem criar uma fonte pessoal sem confirmação explícita.

A pesquisa web institucional, quando habilitada, permanece separada da consulta local. O legado permite fontes oficiais como `stj.jus.br`, `stf.jus.br`, `cnj.jus.br`, `planalto.gov.br` e `senado.leg.br`, com HTTPS, validação de host e proteção contra SSRF. Nenhum resultado web deve ser tratado como confiável apenas porque veio de uma busca; ele precisa manter URL, origem e aviso de conferência.

## Contrato da recomendação

A nova rota pode ser:

```text
POST /projects/<project_id>/ai/legal-recommendations
```

Entrada mínima:

```json
{
  "request_id": "uuid",
  "project_revision": 12,
  "problem_question": "...",
  "professor_instructions": "...",
  "keywords": ["..."],
  "catalog_source_ids": ["vademecum-2023:...", "stj-...", "ufob-mb:..."]
}
```

O navegador envia somente IDs de catálogo. Título, autor, ementa, referência, ano, tipo e origem são buscados novamente pelo servidor. Metadados enviados pelo navegador não são fonte de verdade.

A resposta deve ter forma equivalente a:

```json
{
  "ok": true,
  "request_id": "uuid",
  "provider": {
    "name": "deepseek",
    "model": "...",
    "fallback_used": false,
    "fallback_reason": null
  },
  "recommendations": {
    "law": [],
    "jurisprudence": [],
    "doctrine": []
  },
  "coverage": {
    "candidate_count": 3,
    "by_kind": {
      "legislation": 1,
      "case-law": 1,
      "book": 1
    },
    "scope": "índice local; pista inicial"
  },
  "warnings": [
    "Confira vigência, inteiro teor e pertinência antes de citar."
  ]
}
```

Cada recomendação deve conter `source_id`, `kind`, metadados canônicos, `why` e `rank`. O servidor rejeita categoria incompatível, ID inexistente, duplicidade, fonte inventada e campos extras. Se não houver candidato de uma categoria, a lista fica vazia e a resposta explica o recorte; ausência no catálogo não prova inexistência da fonte.

## DeepSeek primário e Gemini como fallback

O serviço deve manter uma interface única de saída estruturada, por exemplo `complete_json(messages, schema)`. O adaptador DeepSeek continua usando o endpoint já existente, `response_format: {"type":"json_object"}` e validação local. A documentação oficial do DeepSeek alerta que JSON pode vir vazio ou truncado; por isso o parser precisa rejeitar resposta vazia, JSON inválido e estrutura semanticamente inválida.

O adaptador Gemini deve ser separado no mesmo módulo de provedores. A chave não entra em URL, frontend, banco ou log. A configuração prevista é `GEMINI_API_KEY` ou `GEMINI_API_KEY_FILE`, além de `GEMINI_MODEL` e, se necessário, `GEMINI_API_URL`. O transporte pode usar REST para manter o projeto pequeno; a resposta Gemini é normalizada para o mesmo contrato interno antes de chegar ao domínio.

A política é fechada e não é “tentar qualquer coisa até funcionar”:

- fazer uma tentativa com DeepSeek;
- chamar Gemini uma única vez somente em timeout, falha de conexão, HTTP 408, 429, 5xx, resposta JSON inválida ou resposta grande demais;
- não usar Gemini quando faltarem termos, consentimento, quota, projeto, catálogo ou chave válida;
- não fazer fallback em 401/402 nem em erro de regra de negócio;
- se os dois falharem, devolver erro seguro e reembolsar a reserva;
- se DeepSeek produzir resposta válida, nunca chamar Gemini;
- informar no resultado qual provedor respondeu e se houve fallback.

A rota continua verificando termos, consentimento, CSRF, propriedade do projeto e revisão salva antes de ler secrets ou chamar qualquer provedor. Uma requisição DeepSeek mais um eventual Gemini consome uma única unidade de uso. `request_id` UUID e uma reserva transacional impedem duplo débito em reenvio ou corrida entre abas.

O JEV/Typesafe existente não deve ser usado como fallback do Gemini. Ele permanece como avaliador separado enquanto a paridade com o legado for necessária. A primeira versão da recomendação pode usar DeepSeek/Gemini para gerar a estrutura e JEV para validar pertinência, sem misturar os contratos.

## Google Scholar: o que é possível

Google Scholar é útil para artigos, teses, livros, citações e opiniões judiciais, mas não fornece uma API oficial nem acesso em massa. A própria ajuda do Google informa que não libera acesso em massa e pede respeito ao `robots.txt`; scraping direto não será colocado no Assistente.

A solução segura é dividir a necessidade em três caminhos. O catálogo local continua sendo a fonte jurídica determinística. A busca oficial permitida continua sendo usada para Planalto, STJ, STF, CNJ e Senado. Uma integração Google Scholar pode ser criada como adaptador opcional de terceiro, por exemplo SerpApi, com chave separada, limite de uso, cache e aviso de que o resultado é externo. Ela não deve ser requisito para o site funcionar.

Não usaremos a ferramenta Google Search do Gemini como substituta automática do Scholar. O grounding do Gemini pesquisa a web geral e devolve citações de URL, mas não garante que cada resultado seja de Google Scholar, nem substitui a proveniência dos corpora jurídicos. Se for habilitado no futuro, será uma etapa explícita de pesquisa externa, com custo e origem mostrados ao usuário.

A ordem recomendada é: primeiro recuperar os três corpora e a pesquisa contextual do legado; depois criar o adaptador Scholar opcional; somente depois avaliar grounding do Gemini para consultas acadêmicas abertas. Isso evita pagar por busca externa enquanto o acervo básico ainda não está correto.

## Organização da implementação

### Fase 1 — Recuperar o acervo e seus contratos

Portar os importadores do legado, montar o catálogo no volume externo do VPS, registrar metadados de origem e criar fixtures pequenas para Vade 2023, livros UFOB 2021 e ementas STJ. Validar IDs, deduplicação, anos, origem e a distinção entre ementa e inteiro teor.

Critério de aceite: o catálogo interno mantém as três bases reais e a aplicação permanece utilizável quando ele está ausente ou somente leitura; a Biblioteca Pessoal continua restrita a fontes e fichamentos.

### Fase 2 — Recolocar a pesquisa dentro do trabalho

Adicionar a ferramenta de pesquisa à etapa de fontes do editor. Reutilizar os campos já existentes de `assignment_prompt`, professor, pergunta-problema, teses, objeto, teoria e `keywords`. Repor a busca local contextual e a resposta de referências, sem chamar IA na consulta simples.

Critério de aceite: o usuário consegue pesquisar, visualizar origem/ano/referência/ementa e escolher candidatos sem que nenhum resultado seja cadastrado automaticamente.

### Fase 3 — Repor pesquisa contextual e validação

Criar o domínio `legal_recommendations`, o serviço de contexto, a rota autenticada e os contratos de `request_id`, reserva, finalização e reembolso. Repor as ações especializadas do legado gradualmente, começando por pesquisa de referências e depois sugestões de pergunta-problema, teses e revisão de referências.

Critério de aceite: a IA usa pergunta-problema e instruções do professor, separa Lei/Jurisprudência/Doutrina, só aponta IDs existentes e oferece aplicar/editar/descartar.

### Fase 4 — Adicionar Gemini

Implementar `GeminiClient` fakeável, fixtures de respostas válidas e inválidas, matriz de fallback e variáveis de configuração sem secrets no Git. O Gemini entra primeiro somente como fallback técnico, não como segundo resultado concorrente nem como busca web automática.

Critério de aceite: DeepSeek válido gera uma única chamada; timeout/5xx do DeepSeek gera no máximo uma chamada Gemini; erro de consentimento, quota ou configuração não chama Gemini; resposta inválida dos dois reembolsa a reserva.

### Fase 5 — Pesquisa acadêmica externa opcional

Criar um adaptador separado para um provedor de resultados do Google Scholar, inicialmente desativado. A resposta fica marcada como externa, com cache, limite e URL original. O contrato não mistura esses resultados com o corpus STJ, Vade ou livros 2021.

Critério de aceite: sem chave do provedor, a aplicação funciona normalmente; com chave, o usuário vê custo/limite e origem; nenhuma chamada é feita durante autosave ou abertura do editor.

## Testes obrigatórios

Os testes de domínio devem cobrir separação de categorias, IDs inexistentes, fontes incompatíveis, resposta vazia, ausência de professor e ausência de candidatos. Os testes do catálogo interno devem verificar FTS, fallback sem FTS, deduplicação, anos e proveniência dos três corpora, sem criar uma rota de consulta na Biblioteca.

Os testes de provedores devem usar transportes falsos. É necessário provar que DeepSeek válido não chama Gemini, que falha técnica chama Gemini uma vez, que falha de autenticação não faz fallback, que JSON inválido é rejeitado e que nenhum prompt ou resposta aparece em logs.

Os testes de rota devem cobrir termos, consentimento, CSRF, projeto alheio, revisão velha, UUID repetido, quota, ausência de catálogo e reembolso. O teste de navegador deve conferir a ferramenta dentro da etapa de fontes, os três blocos de resultados, aplicar/editar/descartar, aviso de ementa, ausência de cadastro automático e preservação do autosave.

Nenhum teste chama Google, DeepSeek, Gemini, JEV ou provedor Scholar real. Staging usa banco temporário, fixtures do catálogo e rede bloqueada para os testes automatizados.

## Arquivos previstos

A implementação deve reutilizar `app/services/research.py`, `app/services/assistant.py`, `app/services/providers.py`, `app/routes/ai.py`, `app/routes/library.py`, `templates/projects/editor.html` e `static/js/project-editor.js` antes de criar módulos novos.

Os novos limites devem ficar pequenos e explícitos: `app/domain/legal_recommendations.py` para normalização e validação; um serviço de recomendação contextual; um adaptador Gemini no módulo de provedores; e testes por contrato. Os importadores do legado devem ficar em `scripts/` e a documentação do catálogo deve explicar como atualizá-los. Não criar uma segunda biblioteca, um segundo banco de usuários ou um agente autônomo separado.

## Estado desta decisão

As fases 1–4 estão implementadas no produto principal: os importadores e o catálogo externo já existem, a pesquisa contextual aparece no ponto de fundamentação do Case, as recomendações são separadas por categoria, os assistentes especializados e a avaliação JEV foram recuperados dentro das etapas, e o fallback DeepSeek→Gemini foi validado com transportes falsos. A chave Gemini fica opcional no secret operacional do VPS. A fase 5, pesquisa acadêmica externa/Scholar, continua desativada e exige provedor separado e política de uso antes de qualquer código.

## Referências externas

As referências a seguir fundamentam somente as capacidades e limitações dos serviços externos. Os comportamentos do produto legado foram confirmados nos arquivos e funções citados ao longo deste documento.

[1]: https://ai.google.dev/gemini-api/docs/structured-output "Gemini API structured outputs"
[2]: https://ai.google.dev/gemini-api/docs/quickstart "Gemini API getting started"
[3]: https://ai.google.dev/gemini-api/docs/google-search "Gemini API grounding with Google Search"
[4]: https://api-docs.deepseek.com/guides/json_mode/ "DeepSeek JSON Output"
[5]: https://api-docs.deepseek.com/guides/search/ "DeepSeek Search and Fetch"
[6]: https://scholar.google.com/intl/en/scholar/about.html "Google Scholar About"
[7]: https://scholar.google.com/intl/en/scholar/help.html "Google Scholar Search Help"
[8]: https://serpapi.com/google-scholar-api "SerpApi Google Scholar API"
