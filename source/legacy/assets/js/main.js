const STORAGE_KEY = "roteiro-report-project-v2";
const LEGACY_STORAGE_KEY = "roteiro-draft-v1:case";
const LEGACY_PAPER_STORAGE_KEY = "roteiro-draft-v1:paper";
const app = document.querySelector("#app");
const sourceTypes = [
  ["legal", "Legal"],
  ["case-law", "Jurisprudencial"],
  ["doctrine", "Doutrinária"],
];
const referenceTypes = [
  ["manual", "Referência digitada manualmente"],
  ["book", "Livro"],
  ["article", "Artigo em periódico"],
  ["online", "Página ou documento online"],
  ["legislation", "Legislação"],
  ["case-law", "Jurisprudência ou decisão judicial"],
];
const thesisLabels = { A: "Tese A", B: "Tese B" };
const caseAnalysisCategories = ["Insuficiente", "Parcial", "Adequado"];
const AI_CHECKLIST_SUGGESTION_THRESHOLD = 0.7;
const AI_REVIEW_EXCLUDED_FIELDS = new Set([
  "assignmentPrompt", "author", "institution", "course", "discipline", "teacher",
  "classInfo", "deliveryDate", "city", "year", "profile", "paperKind",
]);
const caseGradeRanges = [
  "0,00–0,87 ponto",
  "0,88–1,75 ponto",
  "1,76–2,62 pontos",
  "2,63–3,50 pontos",
];
const referenceFields = {
  book: [
    ["authors", "Autor(es) como aparecem na referência", true],
    ["title", "Título e subtítulo", true],
    ["edition", "Edição (se não for a primeira)", false],
    ["city", "Local", true],
    ["publisher", "Editora", true],
    ["year", "Ano", true],
  ],
  article: [
    ["authors", "Autor(es) como aparecem na referência", true],
    ["title", "Título do artigo", true],
    ["journal", "Nome do periódico", true],
    ["city", "Local", false],
    ["volume", "Volume", false],
    ["issue", "Número", false],
    ["pages", "Páginas inicial-final", true],
    ["monthYear", "Mês e ano", true],
  ],
  online: [
    ["authors", "Autor ou organização", true],
    ["title", "Título da página ou documento", true],
    ["site", "Nome do site ou publicação", false],
    ["year", "Ano", false],
    ["url", "URL", true],
    ["accessDate", "Data de acesso", true],
  ],
  legislation: [
    ["jurisdiction", "País, estado ou município", true],
    ["title", "Tipo e identificação da norma", true],
    ["date", "Data da norma", true],
    ["ementa", "Ementa", false],
    ["publication", "Publicação oficial", false],
    ["url", "URL", false],
    ["accessDate", "Data de acesso (se consultada online)", false],
  ],
  "case-law": [
    ["jurisdiction", "País, estado ou órgão responsável", true],
    ["tribunal", "Tribunal", true],
    ["party", "Parte (quando aplicável)", false],
    ["processType", "Tipo da decisão ou processo", true],
    ["processNumber", "Número do processo", true],
    ["rapporteur", "Relator(a)", true],
    ["judgedAt", "Data do julgamento", true],
    ["courtBody", "Órgão julgador", false],
    ["publication", "Diário ou repositório oficial", false],
    ["url", "URL", false],
    ["accessDate", "Data de acesso (se consultada online)", false],
  ],
};

function emptyProject(projectType = "case") {
  return {
    version: 2,
    projectType,
    fields: {
      profile: "facsure",
      paperKind: "project",
      institution: "Faculdade Supremo Redentor — FACSUR",
      course: "Direito",
      city: "Pinheiro — MA",
      year: String(new Date().getFullYear()),
      title: "",
      author: "",
      assignmentPrompt: "",
      originalCasePrompt: "",
      discipline: "",
      teacher: "",
      classInfo: "",
      deliveryDate: "",
      facts: "",
      problem: "",
      decisionBasis: "",
      decisionA: "",
      decisionB: "",
      thesisATitle: "",
      thesisA: "",
      thesisBTitle: "",
      thesisB: "",
      area: "",
      delimitation: "",
      researchContext: "",
      researchObject: "",
      problemContext: "",
      hypothesis: "",
      justification: "",
      objectiveGeneral: "",
      objective1: "",
      objective2: "",
      objective3: "",
      theory: "",
      methodAuthor: "",
      nature: "",
      approach: "",
      ends: "",
      procedure: "",
      instruments: "",
      abstract: "",
      keywords: "",
      aiNote: "",
      introduction: "",
      development1Title: "",
      development1: "",
      development2Title: "",
      development2: "",
      development3Title: "",
      development3: "",
      developmentSections: [{ id: newId(), title: "", content: "" }],
      conclusion: "",
    },
    sources: [],
    criteria: [],
    checks: {},
    suggestedChecks: {},
    currentStep: 0,
    finalized: false,
  };
}

const caseStages = [
  {
    title: "Identificação",
    intro: "Informe os dados do relatório e, se quiser usar a assistência contextual, registre a proposta ou as instruções do professor.",
    fields: [
      { id: "title", label: "Título do relatório", required: true },
      { id: "author", label: "Autor(es)", type: "textarea", hint: "Escreva um nome por linha.", required: true },
      { id: "assignmentPrompt", label: "Proposta ou instruções do professor", type: "textarea", size: "large", hint: "Necessária para pedir uma revisão contextual por IA. O texto é enviado junto com os campos acadêmicos relevantes somente quando você solicitar." },
      { id: "profile", label: "Modelo de formatação", type: "select", options: [["facsure", "Referência FACSUR"], ["livre", "Formato livre"]] },
      { id: "institution", label: "Instituição" },
      { id: "course", label: "Curso" },
      { id: "discipline", label: "Disciplina" },
      { id: "teacher", label: "Professor(a)" },
      { id: "classInfo", label: "Turma e período" },
      { id: "deliveryDate", label: "Data de entrega", placeholder: "28/09/2026" },
      { id: "city", label: "Cidade e estado" },
      { id: "year", label: "Ano" },
    ],
  },
  {
    title: "1 · Descrição do caso",
    intro: "Reescreva a situação com suas palavras. Apresente somente os fatos relevantes e feche com uma pergunta jurídica clara.",
    analysisSection: "case_description",
    fields: [
      { id: "originalCasePrompt", label: "Enunciado original fornecido pelo professor (opcional)", type: "textarea", size: "large", hint: "Se quiser conferir se a narrativa está redigida com suas próprias palavras, cole aqui o enunciado recebido. Ele será enviado somente ao pedir a avaliação desta etapa. Não use dados pessoais desnecessários." },
      { id: "facts", label: "Narrativa dos fatos", type: "textarea", size: "large", hint: "Use a sequência quem está envolvido, o que aconteceu, contexto e conflito. Evite copiar o enunciado ou antecipar uma solução.", required: true },
      { id: "problem", label: "Pergunta-problema", type: "textarea", hint: "Termine a seção com uma pergunta aberta, ligada aos fatos e sem anunciar as teses.", required: true },
    ],
    checks: [
      ["facts-original", "Reescrevi os fatos com minhas próprias palavras, sem copiar o enunciado."],
      ["facts-neutral", "Mantive a descrição sem antecipar solução ou julgamento."],
      ["facts-relevant", "Apresentei quem, o que, contexto e conflito e cortei o que não altera o caso."],
      ["problem-question", "A seção termina com uma pergunta jurídica clara, não respondível apenas com sim ou não."],
    ],
  },
  {
    title: "2.1 · Decisões possíveis",
    intro: "Apresente a base conceitual que torna o caso discutível e formule duas alternativas juridicamente plausíveis, em tom neutro.",
    analysisSection: "case_decisions",
    fields: [
      { id: "decisionBasis", label: "Base conceitual", type: "textarea", hint: "Explique brevemente os conceitos ou institutos que sustentam as alternativas." , required: true },
      { id: "decisionA", label: "Decisão possível A", type: "textarea", hint: "Redija como alternativa jurídica, não como descrição dos fatos.", required: true },
      { id: "decisionB", label: "Decisão possível B", type: "textarea", hint: "Dê a esta alternativa peso jurídico comparável à alternativa A.", required: true },
    ],
    checks: [
      ["decisions-clear", "As duas decisões possíveis estão formuladas com clareza."],
      ["decisions-balanced", "As alternativas têm peso jurídico comparável."],
      ["decisions-neutral", "A base conceitual e a apresentação não indicam uma preferência."],
    ],
  },
  {
    title: "2.2.1 · Argumentação da tese A",
    intro: "Desenvolva a primeira linha argumentativa. Integre legislação, doutrina e jurisprudência e explique como cada fonte se relaciona com o problema. Nas citações diretas, indique a página; citações longas (mais de três linhas) usam recuo de 4 cm, fonte 10 e espaçamento simples conforme o manual.",
    analysisSection: "thesis_a",
    fields: [
      { id: "thesisATitle", label: "Título da linha argumentativa A", placeholder: "Síntese da primeira posição" , required: true },
      { id: "thesisA", label: "Argumentação da tese A", type: "textarea", size: "large", hint: "Construa o raciocínio com norma, interpretação doutrinária, decisão judicial e análise própria. Após cada citação, explique sua relevância.", required: true },
    ],
    checks: [
      ["thesis-a-integrated", "Entrelacei legislação, doutrina e jurisprudência na argumentação."],
      ["thesis-a-comment", "Expliquei com palavras próprias a relevância das citações para o caso."],
      ["thesis-a-neutral", "Mantive a análise equilibrada e redigida em terceira pessoa."],
      ["thesis-a-length", "Revisei a extensão da tese A conforme a orientação de aproximadamente duas laudas."],
    ],
  },
  {
    title: "2.2.2 · Argumentação da tese B",
    intro: "Desenvolva a segunda linha com o mesmo cuidado e extensão da primeira, sem transformar uma das posições em argumento artificialmente fraco. Nas citações diretas, indique a página; citações longas (mais de três linhas) usam recuo de 4 cm, fonte 10 e espaçamento simples conforme o manual.",
    analysisSection: "thesis_b",
    fields: [
      { id: "thesisBTitle", label: "Título da linha argumentativa B", placeholder: "Síntese da segunda posição", required: true },
      { id: "thesisB", label: "Argumentação da tese B", type: "textarea", size: "large", hint: "Integre lei, doutrina e decisões judiciais; depois de cada citação, explique a conexão com o problema.", required: true },
    ],
    checks: [
      ["thesis-b-integrated", "Entrelacei legislação, doutrina e jurisprudência na argumentação."],
      ["thesis-b-comment", "Expliquei com palavras próprias a relevância das citações para o caso."],
      ["thesis-b-neutral", "Mantive a análise equilibrada e redigida em terceira pessoa."],
      ["thesis-b-length", "Revisei a extensão da tese B conforme a orientação de aproximadamente duas laudas."],
    ],
  },
  {
    title: "2.3 · Critérios e valores",
    intro: "Liste os conceitos técnicos e princípios usados nas teses, definindo cada um e indicando sua base normativa ou ética.",
    analysisSection: "criteria_and_values",
    custom: "criteria",
    checks: [
      ["criteria-defined", "Defini os conceitos técnicos relevantes e indiquei o fundamento de cada definição."],
      ["criteria-covered", "Conferi se os termos técnicos usados nas teses estão explicados nesta seção."],
    ],
  },
  {
    title: "Referências",
    intro: "Organize as fontes por categoria durante a elaboração. O relatório reúne apenas as obras citadas no texto, em uma lista alfabética única; revise cada referência conforme a ABNT e as orientações da disciplina.",
    analysisUnavailable: "Esta checklist depende de conferir a lista de referências, citações no documento e regras de formatação. Esses dados não são enviados para avaliação automática; faça esta conferência manualmente.",
    custom: "sources",
    checks: [
      ["references-elements", "Conferi os elementos de identificação e localização de cada obra, inclusive URL e data de acesso quando aplicáveis."],
      ["references-cited", "Incluí somente fontes citadas no texto e conferi a correspondência entre citações e referências."],
      ["references-author", "Usei autoria pessoal ou institucional de forma consistente; para quatro autores ou mais, conferi a indicação et al. conforme o manual."],
      ["references-alpha", "Conferi que a lista final está em ordem alfabética única."],
      ["references-abnt", "Revisei a apresentação das referências conforme a ABNT e as orientações da disciplina."],
    ],
  },
  {
    title: "Revisão do relatório",
    intro: "Confira os critérios atendidos e o que ainda falta. O indicador mede a lista de requisitos e as fontes registradas; não avalia a correção jurídica dos argumentos.",
    custom: "review",
  },
];

const civilCaseModel = {
  id: "civil-personality",
  typeLabel: "Relatório de case · Modelo preenchido",
  pdfDataAttribute: "caseModelPdf",
  title: "Direito da Personalidade",
  authors: "Ítalo Gustavo Pinheiro Diniz\nSivaldo Davi Pereira",
  discipline: "Direito Civil I",
  teacher: "Alana Raissa Martins Pinheiro Furtado",
  classInfo: "Noturno, 2º período",
  deliveryDate: "29/09/2026",
  city: "Pinheiro — MA",
  year: "2026",
  sections: [
    {
      title: "1 DESCRIÇÃO DO CASO",
      paragraphs: [
        "Helena, uma influenciadora digital com um grande número de seguidores nas redes sociais, estava produzindo uma série de vídeos sobre uma clínica de estética. Durante uma visita ao local, percebeu um intenso alvoroço e decidiu verificar o que estava acontecendo. Ao chegar, constatou que uma paciente encontrava-se em estado de euforia, manifestando forte insatisfação com o procedimento estético realizado.",
        "Diante da possibilidade de gerar um conteúdo viral, Helena iniciou a gravação, registrando imagens da fachada e do interior da clínica, bem como do médico responsável, Dr. Rafael, e de uma paciente identificada como Marina. Posteriormente, publicou o vídeo acompanhado da seguinte legenda: “Até quando clínicas poderão esconder dos pacientes o que realmente acontece dentro de seus consultórios?”.",
        "O vídeo alcançou aproximadamente 600 mil visualizações, gerando ampla repercussão. Em razão disso, o Dr. Rafael ingressou com ação judicial, alegando ter sofrido prejuízos significativos em decorrência da circulação do vídeo, o qual, segundo ele, induzia o público a acreditar que realizava procedimentos ilegais. Marina também ajuizou ação por danos morais contra Helena, sustentando que fora filmada sem consentimento, o que teria acarretado grave prejuízo à sua reputação.",
        "Diante do ocorrido, quais são os limites da liberdade de expressão quando esta colide com direitos de terceiros, especialmente no que se refere à proteção da honra, da imagem e da reputação?",
      ],
    },
    {
      title: "2 IDENTIFICAÇÃO E ANÁLISE DO CASO",
      paragraphs: [],
    },
    {
      title: "2.1. Descrição das decisões possíveis",
      paragraphs: [
        "O caso apresenta o limite do direito a liberdade de expressão frente ao direito da personalidade. Pelo primeiro, \"todo ser humano tem direito à liberdade de opinião e expressão; este direito inclui a liberdade de [...] procurar, receber e transmitir informações e ideias por quaisquer meios[...]\" (Declaração Universal dos Direitos Humanos, 1948); pelo segundo \"[se tem] o direito da pessoa de defender o que lhe é próprio, ou seja, a sua integridade física [...], a sua integridade intelectual [...] e a sua integridade moral [...]\" (Diniz, 2025, p. 218).",
        "Ambos os direitos tem previsão legal: liberdade de expressão esta prevista na Constituição Federal (art. 5º, incisos IV e IX; art. 220), já a personalidade, em especial, no Código Civil (arts. 11 a 21). Além disso, o Marco Civil da Internet, o qual rege as relações entre os internautas, prevê em seu artigo 19 a responsabilidade civil e liberdade no contexto internético (que se aplica ao caso, pois foi feita divulgação pública e informática das imagens).",
        "No caso concreto, a Helena se utiliza da liberdade de expressão mas, conforme alega a defesa do Dr. Rafael e da Marina, não observa que existe direito da personalidade, atingindo-lhes [os ofendidos] a honra, imagem e reputação. Os dois direitos devem ser ponderados, a fim de entender qual deles prevalecerá.",
        "Diante dessa análise, existem duas soluções juridicamente possíveis:",
        "a) Os limites da liberdade de expressão findam quando se atinge o direito de terceiros, principalmente a honra e a imagem.\nb) Os limites da liberdade de expressão não findam, mesmo que se atinja a honra e a imagem de terceiros, quando há denúncia de interesse público.",
      ],
    },
    {
      title: "2.2 Descrição dos argumentos",
      paragraphs: [],
    },
    {
      title: "2.2.1 Os limites da liberdade de expressão findam quando se atinge o direito de terceiros, principalmente a honra e a imagem",
      paragraphs: [
        "A liberdade de expressão é, como todos direito fundamental, não absoluto. Assim, quando esbarra em outro, como o da personalidade, pode ser limitada em favor da defesa de outro bem jurídico mais importante; no caso concreto: a imagem e honra.",
        "É garantia da Constituição Federal de 1988 a liberdade de expressão, conforme o artigo 5º, inciso IV: “é livre a manifestação do pensamento, sendo vedado o anonimato” (Brasil, Constituição, 1988). Desse modo, o direito de expressão do cidadão brasileiro possui amparo constitucional sendo lícito o seu pleno exercício. Segundo Bentivegna (2019), a liberdade de expressão abrange, de forma ampla, a livre manifestação do pensamento e da opinião. Este é um dos direitos que integram o rol dos direitos da personalidade previstos no Código Civil de 2002.",
        "A dignidade da pessoa humana, assim como a honra e a privacidade, são outros direitos da personalidade garantidos pelo ordenamento jurídico brasileiro. Segundo Bentivegna, a personalidade pode ser compreendida sob dois diferentes aspectos:",
        { quote: "Para parte da doutrina o termo personalidade não é unívoco, podendo ser considerado sob dois diferentes aspectos: a) um ponto de vista estrutural, porquanto respeite à estrutura das situações jurídicas subjetivas, em que a pessoa “tomada em sua subjetividade, identifica-se como o elemento subjetivo das relações jurídicas”. Nesta acepção, é o atributo da pessoa que a habilita a ser titular de relações jurídicas, ou seja, a ser sujeito de direitos e deveres; b) um outro ponto de vista que concebe a personalidade como o conjunto de características e atributos da pessoa e objeto de proteção por parte do ordenamento jurídico (Bentivegna, 2019, p. 6)." },
        "Percebe-se que, para o autor, a doutrina - embora diferencie as duas visões em aspectos formais e materiais - concorda no sentido de reconhecer que a personalidade possui direito à tutela jurídica.",
        "No caso concreto, a defesa de Helena sustentou que estava exercendo seu direito à liberdade de expressão e que a retirada do vídeo configuraria censura. Contudo, o Código Civil de 2002, em seu artigo 20, dispõe:",
        { quote: "Salvo se autorizadas, ou se necessárias à administração da justiça ou à manutenção da ordem pública, a divulgação de escritos, a transmissão da palavra, ou a publicação, a exposição ou a utilização da imagem de uma pessoa poderão ser proibidas, a seu requerimento e sem prejuízo da indenização que couber, se lhe atingirem a honra, a boa fama ou a respeitabilidade, ou se se destinarem a fins comerciais (Brasil, Código Civil, 2002, art. 20)." },
        "Na situação em análise, verificou-se, além da violação à honra e à imagem, que o Dr. Rafael comprovou prejuízos materiais, como a perda de contratos profissionais e o cancelamento de consultas, decorrentes da associação de sua imagem a supostas irregularidades. A paciente Mariana, por sua vez, teve sua imagem divulgada sem consentimento, o que expôs aspectos de sua vida privada e gerou constrangimento social e exposição indevida de sua intimidade, em clara violação ao artigo 20 do Código Civil. Assim, conclui-se que a alegação de Helena não encontra respaldo no ordenamento jurídico brasileiro, uma vez que a publicação dos vídeos ocasionou prejuízos ao Dr. Rafael e à paciente Mariana. Dessa forma, a retirada dos vídeos é juridicamente possível, sem que se configure censura. Esses elementos demonstram que a liberdade de expressão, quando exercida de forma abusiva, pode gerar não apenas danos morais, mas também patrimoniais, exigindo limites jurídicos.",
        "Nesse contexto, Souza e Giacomelli (2018) sustentam que a liberdade de expressão encontra limites quando se choca com outros direitos, como a honra e a imagem. O artigo 220, caput e § 1º, da Constituição Federal dispõe que é livre a manifestação do pensamento no Brasil, desde que resguardados os direitos previstos no artigo 5º (Brasil, 1988). Assim, reafirma-se que nenhum direito é absoluto, impondo-se a necessária ponderação entre princípios constitucionais.",
        "Essa compreensão também é acolhida pela jurisprudência do Supremo Tribunal Federal. Na ADPF 130/DF, ao tratar da liberdade de imprensa, o STF afirmou que não há direito fundamental absoluto, devendo-se sempre realizar a ponderação entre princípios constitucionais em conflito. Nesse julgamento, destacou-se que a liberdade de expressão, embora essencial à democracia, não pode servir de escudo para práticas que violem a honra, a imagem ou a dignidade da pessoa humana, impondo-se a responsabilização posterior por eventuais abusos.",
        "Em síntese, a liberdade de expressão possui respaldo constitucional e seu exercício é plenamente válido no ordenamento jurídico brasileiro. Contudo, tanto a legislação quanto a jurisprudência reconhecem que nenhum direito é absoluto, impondo-se a necessária ponderação conforme o artigo 5º da Constituição Federal, que trata dos direitos e garantias fundamentais. Na hipótese examinada, a defesa de Helena sustentou que estava em gozo de seu direito e, por isso, não poderia ser penalizada. Entretanto, o Dr. Rafael e a paciente Mariana são assegurados pela justiça brasileira no sentido de que seus direitos não podem ser violados em razão do exercício abusivo de direitos de terceiros. Dessa forma, prevalece o entendimento de que, diante da colisão de princípios, a honra e a imagem dos requerentes devem ser protegidas, ainda que isso implique restrição proporcional à liberdade de expressão de Helena.",
      ],
    },
    {
      title: "2.2.2 Os limites da liberdade de expressão não findam, mesmo que se atinja a honra e a imagem de terceiros, quando há denúncia de interesse público",
      paragraphs: [
        "A liberdade de expressão é um direito fundamental, previsto constitucionalmente no artigo 5, inciso IV, cujo diz que “é livre a manifestação do pensamento, sendo vedado o anonimato” (Brasil, Constituição, 1988). A honra e a imagem de terceiros, portanto direitos de personalidade, não prevalecem quando se trata assuntos de pessoa notória e de interesse público.",
        "O médico responsável pela clinica é notório no contexto de sua atividade profissional, sendo ele, conforme as lições de Cavalieri Filho, (2026, p. 142) “profissionalmente ligado ao público”, não podendo “reclamar um direito de imagem com a mesma extensão daquele conferido aos particulares não comprometidos com a publicidade”. Ora, não se pode aplicar o direito a imagem ao dr. Rafael, naquele contexto, da mesma forma que se aplicaria a um civil.",
        "Seguindo o mesmo entendimento do doutrinador, a ministra Nancy Andrighi, do STJ, em voto no REsp 1.082.878/RJ, ponderou que a \"doutrina e jurisprudência são pacíficas no entendimento de que pessoas públicas e/ou notórias têm seu direito de imagem mais restrito que pessoas que não ostentem tal característica\" (Brasil, 2008, p. 6).",
        "Além disso, o fato ocorreu em um local de acesso ao público (o interior da clínica), durante o atendimento, não em um local estritamente privado, mas um ambiente de prestação de serviço de interesse coletivo. Portanto, é à coletividade, e não individualidade, que interessa.",
        "E o interesse coletivo se demonstra, ainda mais, em face da denúncia, que consistiu na divulgação de possíveis irregularidades. A importância se prova, pois, envolve a saúde, o que concorda Bittar (2015, p. 158) ao dizer que “o direito à imagem sofre, como todos os direitos privados, certas limitações decorrentes de exigências da coleti- vidade”.",
        "O atual ministro do STF, Luís Roberto Barroso (2026, p. 227), entende que há “alguns [...] elementos a serem ponderados no conflito entre liberdade de expressão/informação e direitos da personalidade”, citando entre estes a “personalidade pública ou privada da pessoa objeto da notícia” e a “existência de interesse público na divulgação do fato”. Assim, tanto a personalidade, no contexto, é notória e, portanto pública; quanto o assunto é de interesse público demonstrado.",
        "Com isso, a liberdade de expressão não ultrapassou os limites do direito da personalidade, validando-se por se tratar de uma denúncia pública de interesse coletivo e notável relevância.",
      ],
    },
    {
      title: "2.3. Descrição dos critérios e valores",
      paragraphs: [
        "A solução do caso deve ser orientada pelos seguintes critérios e valores jurídicos:",
        "a) Direito da personalidade: é o direito a personalidade própria, que inclui integridade física (ex.: imagem e corpo) e psicológica;\nb) Liberdade de expressão: direito que possibilita expressa opinião e pensamento livremente.\nC) Ponderação: aplicação de um princípio/direito em detrimento a outro a depender do caso concreto, sem hierarquizá-los genericamente.",
      ],
    },
  ],
  citations: [
    { type: "Citação direta", text: "“todo ser humano tem direito à liberdade de opinião e expressão; este direito inclui a liberdade de [...] procurar, receber e transmitir informações e ideias por quaisquer meios[...]” (Declaração Universal dos Direitos Humanos, 1948)." },
    { type: "Citação direta", text: "“é livre a manifestação do pensamento, sendo vedado o anonimato” (Brasil, Constituição, 1988)." },
    { type: "Citação indireta narrativa", text: "Segundo Bentivegna (2019), a liberdade de expressão abrange, de forma ampla, a livre manifestação do pensamento e da opinião." },
    { type: "Citação direta longa", text: "Trecho em bloco, sem aspas externas, com autoria, ano e página ao final: (Bentivegna, 2019, p. 6)." },
    { type: "Citação jurisprudencial", text: "“doutrina e jurisprudência são pacíficas no entendimento de que pessoas públicas e/ou notórias têm seu direito de imagem mais restrito que pessoas que não ostentem tal característica” (Brasil, 2008, p. 6)." },
  ],
  sources: [
    { category: "Doutrinária", reference: "BARROSO, Luís R. Curso de Direito Constitucional Contemporâneo. 14. ed. Rio de Janeiro: SRV, 2026. E-book. ISBN 9786551771620. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9786551771620/. Acesso em: 29 set. 2026." },
    { category: "Doutrinária", reference: "BENTIVEGNA, Carlos Frederico B. Liberdade de expressão, honra, imagem e privacidade: os limites entre o lícito e o ilícito. Barueri: Manole, 2019. ISBN 9788520463321. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9788520463321/. Acesso em: 19 set. 2026." },
    { category: "Doutrinária", reference: "BITTAR, Carlos A. Os Direitos da Personalidade. 8. ed. Rio de Janeiro: Saraiva Jur, 2015. E-book. ISBN 9788502208292. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9788502208292/. Acesso em: 29 set. 2026." },
    { category: "Legal", reference: "BRASIL. [Constituição (1988)]. Constituição da República Federativa do Brasil de 1988. Brasília, DF: Presidência da República, [2016]. Disponível em: https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm. Acesso em: 28 set. 2026." },
    { category: "Legal", reference: "BRASIL. Lei nº 10.406, de 10 de janeiro de 2002. Institui o Código Civil. Brasília, DF: Presidência da República, [2002]. Disponível em: https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm. Acesso em: 29 set. 2026." },
    { category: "Legal", reference: "BRASIL. Lei nº 12.965, de 23 de abril de 2014. Estabelece princípios, garantias, direitos e deveres para o uso da Internet no Brasil. Brasília, DF: Presidência da República, 2014. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm. Acesso em: 29 set. 2026." },
    { category: "Jurisprudencial", reference: "BRASIL. Superior Tribunal de Justiça. Recurso Especial nº 1.082.878/RJ. Brasília, DF: Superior Tribunal de Justiça, [2008]. Disponível em: https://www.stj.jus.br/websecstj/cgi/revista/REJ.cgi/ATC?seq=4291616&. Acesso em: 29 set. 2026." },
    { category: "Jurisprudencial", reference: "BRASIL. Supremo Tribunal Federal. Tema 562 da Repercussão Geral. Brasília, DF: Supremo Tribunal Federal, [2020]. Disponível em: https://portal.stf.jus.br/jurisprudenciaRepercussao/tema.asp?num=562. Acesso em: 29 set. 2026." },
    { category: "Jurisprudencial", reference: "BRASIL. Supremo Tribunal Federal (Tribunal Pleno). Arguição de Descumprimento de Preceito Fundamental nº 130/DF. Requerente: Partido Trabalhista Brasileiro – PTB. Interessado: Congresso Nacional e Presidente da República. Relator: Min. Carlos Ayres Britto. Julgamento em: 30 abr. 2009. Informa Jurídico, [S. l.], 30 abr. 2009. Disponível em: https://www.stf.jus.br/arquivo/cms/publicacaoBOInternet/anexo/link_download/casos_relevantes/pt/ADPF_130.pdf. Acesso em: 29 set. 2026." },
    { category: "Doutrinária", reference: "CAVALIERI FILHO, Sergio. Programa de Responsabilidade Civil. 17. ed. Rio de Janeiro: Atlas, 2026. E-book. ISBN 9786559778706. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9786559778706/. Acesso em: 29 set. 2026." },
    { category: "Doutrinária", reference: "DINIZ, Maria H. Dicionário Jurídico Universitário. 5. ed. Rio de Janeiro: SRV, 2025. ISBN 9788553623594. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9788553623594/. Acesso em: 29 set. 2026." },
    { category: "Legal", reference: "ORGANIZAÇÃO DAS NAÇÕES UNIDAS (ONU). Declaração Universal dos Direitos Humanos. Adotada em 10 de dez. de 1948. Resolução 217 A (III). Paris, 1948. Disponível em: https://www.unicef.org/brazil/declaracao-universal-dos-direitos-humanos. Acesso em: 19 set. 2026." },
    { category: "Doutrinária", reference: "SOUSA, Cássio V. S.; GIACOMELLI, Cinthia L. F. Direito civil I. Porto Alegre: SAGAH, 2018. ISBN 9788595024441. Disponível em: https://integrada.minhabiblioteca.com.br/reader/books/9788595024441/. Acesso em: 19 set. 2026." },
  ],
  workflow: {
    projectType: "case",
    fields: {
      title: "Direito da Personalidade",
      author: "Ítalo Gustavo Pinheiro Diniz\nSivaldo Davi Pereira",
      profile: "facsure",
      institution: "Faculdade Supremo Redentor — FACSUR",
      course: "Direito",
      discipline: "Direito Civil I",
      teacher: "Alana Raissa Martins Pinheiro Furtado",
      classInfo: "Noturno, 2º período",
      deliveryDate: "29/09/2026",
      city: "Pinheiro — MA",
      year: "2026",
      facts: "Helena, uma influenciadora digital com um grande número de seguidores nas redes sociais, estava produzindo uma série de vídeos sobre uma clínica de estética. Durante uma visita ao local, percebeu um intenso alvoroço e decidiu verificar o que estava acontecendo. Ao chegar, constatou que uma paciente encontrava-se em estado de euforia, manifestando forte insatisfação com o procedimento estético realizado.\n\nDiante da possibilidade de gerar um conteúdo viral, Helena iniciou a gravação, registrando imagens da fachada e do interior da clínica, bem como do médico responsável, Dr. Rafael, e de uma paciente identificada como Marina. Posteriormente, publicou o vídeo acompanhado da seguinte legenda: “Até quando clínicas poderão esconder dos pacientes o que realmente acontece dentro de seus consultórios?”.\n\nO vídeo alcançou aproximadamente 600 mil visualizações, gerando ampla repercussão. Em razão disso, o Dr. Rafael ingressou com ação judicial, alegando ter sofrido prejuízos significativos em decorrência da circulação do vídeo, o qual, segundo ele, induzia o público a acreditar que realizava procedimentos ilegais. Marina também ajuizou ação por danos morais contra Helena, sustentando que fora filmada sem consentimento, o que teria acarretado grave prejuízo à sua reputação.",
      problem: "Diante do ocorrido, quais são os limites da liberdade de expressão quando esta colide com direitos de terceiros, especialmente no que se refere à proteção da honra, da imagem e da reputação?",
      decisionBasis: "O caso apresenta o limite do direito a liberdade de expressão frente ao direito da personalidade. Pelo primeiro, \"todo ser humano tem direito à liberdade de opinião e expressão; este direito inclui a liberdade de [...] procurar, receber e transmitir informações e ideias por quaisquer meios[...]\" (Declaração Universal dos Direitos Humanos, 1948); pelo segundo \"[se tem] o direito da pessoa de defender o que lhe é próprio, ou seja, a sua integridade física [...], a sua integridade intelectual [...] e a sua integridade moral [...]\" (Diniz, 2025, p. 218).\n\nAmbos os direitos tem previsão legal: liberdade de expressão esta prevista na Constituição Federal (art. 5º, incisos IV e IX; art. 220), já a personalidade, em especial, no Código Civil (arts. 11 a 21). Além disso, o Marco Civil da Internet, o qual rege as relações entre os internautas, prevê em seu artigo 19 a responsabilidade civil e liberdade no contexto internético (que se aplica ao caso, pois foi feita divulgação pública e informática das imagens).\n\nNo caso concreto, a Helena se utiliza da liberdade de expressão mas, conforme alega a defesa do Dr. Rafael e da Marina, não observa que existe direito da personalidade, atingindo-lhes [os ofendidos] a honra, imagem e reputação. Os dois direitos devem ser ponderados, a fim de entender qual deles prevalecerá.\n\nDiante dessa análise, existem duas soluções juridicamente possíveis:",
      decisionA: "Os limites da liberdade de expressão findam quando se atinge o direito de terceiros, principalmente a honra e a imagem.",
      decisionB: "Os limites da liberdade de expressão não findam, mesmo que se atinja a honra e a imagem de terceiros, quando há denúncia de interesse público.",
      thesisATitle: "Os limites da liberdade de expressão findam quando se atinge o direito de terceiros, principalmente a honra e a imagem",
      thesisA: [
        "A liberdade de expressão é, como todos direito fundamental, não absoluto. Assim, quando esbarra em outro, como o da personalidade, pode ser limitada em favor da defesa de outro bem jurídico mais importante; no caso concreto: a imagem e honra.",
        "É garantia da Constituição Federal de 1988 a liberdade de expressão, conforme o artigo 5º, inciso IV: “é livre a manifestação do pensamento, sendo vedado o anonimato” (Brasil, Constituição, 1988). Desse modo, o direito de expressão do cidadão brasileiro possui amparo constitucional sendo lícito o seu pleno exercício. Segundo Bentivegna (2019), a liberdade de expressão abrange, de forma ampla, a livre manifestação do pensamento e da opinião. Este é um dos direitos que integram o rol dos direitos da personalidade previstos no Código Civil de 2002.",
        "A dignidade da pessoa humana, assim como a honra e a privacidade, são outros direitos da personalidade garantidos pelo ordenamento jurídico brasileiro. Segundo Bentivegna, a personalidade pode ser compreendida sob dois diferentes aspectos:",
        "Para parte da doutrina o termo personalidade não é unívoco, podendo ser considerado sob dois diferentes aspectos: a) um ponto de vista estrutural, porquanto respeite à estrutura das situações jurídicas subjetivas, em que a pessoa “tomada em sua subjetividade, identifica-se como o elemento subjetivo das relações jurídicas”. Nesta acepção, é o atributo da pessoa que a habilita a ser titular de relações jurídicas, ou seja, a ser sujeito de direitos e deveres; b) um outro ponto de vista que concebe a personalidade como o conjunto de características e atributos da pessoa e objeto de proteção por parte do ordenamento jurídico (Bentivegna, 2019, p. 6).",
        "Percebe-se que, para o autor, a doutrina - embora diferencie as duas visões em aspectos formais e materiais - concorda no sentido de reconhecer que a personalidade possui direito à tutela jurídica.",
        "No caso concreto, a defesa de Helena sustentou que estava exercendo seu direito à liberdade de expressão e que a retirada do vídeo configuraria censura. Contudo, o Código Civil de 2002, em seu artigo 20, dispõe:",
        "Salvo se autorizadas, ou se necessárias à administração da justiça ou à manutenção da ordem pública, a divulgação de escritos, a transmissão da palavra, ou a publicação, a exposição ou a utilização da imagem de uma pessoa poderão ser proibidas, a seu requerimento e sem prejuízo da indenização que couber, se lhe atingirem a honra, a boa fama ou a respeitabilidade, ou se se destinarem a fins comerciais (Brasil, Código Civil, 2002, art. 20).",
        "Na situação em análise, verificou-se, além da violação à honra e à imagem, que o Dr. Rafael comprovou prejuízos materiais, como a perda de contratos profissionais e o cancelamento de consultas, decorrentes da associação de sua imagem a supostas irregularidades. A paciente Mariana, por sua vez, teve sua imagem divulgada sem consentimento, o que expôs aspectos de sua vida privada e gerou constrangimento social e exposição indevida de sua intimidade, em clara violação ao artigo 20 do Código Civil. Assim, conclui-se que a alegação de Helena não encontra respaldo no ordenamento jurídico brasileiro, uma vez que a publicação dos vídeos ocasionou prejuízos ao Dr. Rafael e à paciente Mariana. Dessa forma, a retirada dos vídeos é juridicamente possível, sem que se configure censura. Esses elementos demonstram que a liberdade de expressão, quando exercida de forma abusiva, pode gerar não apenas danos morais, mas também patrimoniais, exigindo limites jurídicos.",
        "Nesse contexto, Souza e Giacomelli (2018) sustentam que a liberdade de expressão encontra limites quando se choca com outros direitos, como a honra e a imagem. O artigo 220, caput e § 1º, da Constituição Federal dispõe que é livre a manifestação do pensamento no Brasil, desde que resguardados os direitos previstos no artigo 5º (Brasil, 1988). Assim, reafirma-se que nenhum direito é absoluto, impondo-se a necessária ponderação entre princípios constitucionais.",
        "Essa compreensão também é acolhida pela jurisprudência do Supremo Tribunal Federal. Na ADPF 130/DF, ao tratar da liberdade de imprensa, o STF afirmou que não há direito fundamental absoluto, devendo-se sempre realizar a ponderação entre princípios constitucionais em conflito. Nesse julgamento, destacou-se que a liberdade de expressão, embora essencial à democracia, não pode servir de escudo para práticas que violem a honra, a imagem ou a dignidade da pessoa humana, impondo-se a responsabilização posterior por eventuais abusos.",
        "Em síntese, a liberdade de expressão possui respaldo constitucional e seu exercício é plenamente válido no ordenamento jurídico brasileiro. Contudo, tanto a legislação quanto a jurisprudência reconhecem que nenhum direito é absoluto, impondo-se a necessária ponderação conforme o artigo 5º da Constituição Federal, que trata dos direitos e garantias fundamentais. Na hipótese examinada, a defesa de Helena sustentou que estava em gozo de seu direito e, por isso, não poderia ser penalizada. Entretanto, o Dr. Rafael e a paciente Mariana são assegurados pela justiça brasileira no sentido de que seus direitos não podem ser violados em razão do exercício abusivo de direitos de terceiros. Dessa forma, prevalece o entendimento de que, diante da colisão de princípios, a honra e a imagem dos requerentes devem ser protegidas, ainda que isso implique restrição proporcional à liberdade de expressão de Helena.",
      ].join("\n\n"),
      thesisBTitle: "Os limites da liberdade de expressão não findam, mesmo que se atinja a honra e a imagem de terceiros, quando há denúncia de interesse público",
      thesisB: [
        "A liberdade de expressão é um direito fundamental, previsto constitucionalmente no artigo 5, inciso IV, cujo diz que “é livre a manifestação do pensamento, sendo vedado o anonimato” (Brasil, Constituição, 1988). A honra e a imagem de terceiros, portanto direitos de personalidade, não prevalecem quando se trata assuntos de pessoa notória e de interesse público.",
        "O médico responsável pela clinica é notório no contexto de sua atividade profissional, sendo ele, conforme as lições de Cavalieri Filho, (2026, p. 142) “profissionalmente ligado ao público”, não podendo “reclamar um direito de imagem com a mesma extensão daquele conferido aos particulares não comprometidos com a publicidade”. Ora, não se pode aplicar o direito a imagem ao dr. Rafael, naquele contexto, da mesma forma que se aplicaria a um civil.",
        "Seguindo o mesmo entendimento do doutrinador, a ministra Nancy Andrighi, do STJ, em voto no REsp 1.082.878/RJ, ponderou que a \"doutrina e jurisprudência são pacíficas no entendimento de que pessoas públicas e/ou notórias têm seu direito de imagem mais restrito que pessoas que não ostentem tal característica\" (Brasil, 2008, p. 6).",
        "Além disso, o fato ocorreu em um local de acesso ao público (o interior da clínica), durante o atendimento, não em um local estritamente privado, mas um ambiente de prestação de serviço de interesse coletivo. Portanto, é à coletividade, e não individualidade, que interessa.",
        "E o interesse coletivo se demonstra, ainda mais, em face da denúncia, que consistiu na divulgação de possíveis irregularidades. A importância se prova, pois, envolve a saúde, o que concorda Bittar (2015, p. 158) ao dizer que “o direito à imagem sofre, como todos os direitos privados, certas limitações decorrentes de exigências da coleti- vidade”.",
        "O atual ministro do STF, Luís Roberto Barroso (2026, p. 227), entende que há “alguns [...] elementos a serem ponderados no conflito entre liberdade de expressão/informação e direitos da personalidade”, citando entre estes a “personalidade pública ou privada da pessoa objeto da notícia” e a “existência de interesse público na divulgação do fato”. Assim, tanto a personalidade, no contexto, é notória e, portanto pública; quanto o assunto é de interesse público demonstrado.",
        "Com isso, a liberdade de expressão não ultrapassou os limites do direito da personalidade, validando-se por se tratar de uma denúncia pública de interesse coletivo e notável relevância.",
      ].join("\n\n"),
      criteriaText: "A solução do caso deve ser orientada pelos seguintes critérios e valores jurídicos:\n\na) Direito da personalidade: é o direito a personalidade própria, que inclui integridade física (ex.: imagem e corpo) e psicológica;\nb) Liberdade de expressão: direito que possibilita expressa opinião e pensamento livremente.\nC) Ponderação: aplicação de um princípio/direito em detrimento a outro a depender do caso concreto, sem hierarquizá-los genericamente.",
    },
    checks: {},
  },
};
const modelSourceTypes = [
  { category: "doctrine", referenceType: "manual" },
  { category: "doctrine", referenceType: "manual" },
  { category: "doctrine", referenceType: "manual" },
  { category: "legal", referenceType: "legislation" },
  { category: "legal", referenceType: "legislation" },
  { category: "legal", referenceType: "legislation" },
  { category: "case-law", referenceType: "case-law" },
  { category: "case-law", referenceType: "case-law" },
  { category: "case-law", referenceType: "case-law" },
  { category: "doctrine", referenceType: "manual" },
  { category: "doctrine", referenceType: "manual" },
  { category: "legal", referenceType: "online" },
  { category: "doctrine", referenceType: "manual" },
];
civilCaseModel.workflow.sources = modelSourceTypes.map((details, index) => ({
  ...details,
  reference: civilCaseModel.sources[index].reference,
  cited: true,
}));
const reportModels = [civilCaseModel];

const paperProjectStages = [
  {
    title: "Identificação e delimitação",
    intro: "Delimite o tema antes de formular o problema. Use o funil do tema e confirme interesse, viabilidade, relevância e competência.",
    fields: [
      { id: "paperKind", label: "Etapa do trabalho", type: "select", options: [["project", "Projeto de Paper"], ["final", "Paper Final"]] },
      { id: "profile", label: "Modelo de formatação", type: "select", options: [["facsure", "Referência FACSUR"], ["livre", "Formato livre"]] },
      { id: "title", label: "Título provisório", required: true },
      { id: "author", label: "Autor(es)", type: "textarea", hint: "Um nome por linha.", required: true },
      { id: "assignmentPrompt", label: "Proposta ou instruções do professor", type: "textarea", size: "large", hint: "Necessária para pedir uma revisão contextual por IA. O texto é enviado junto com os campos acadêmicos relevantes somente quando você solicitar." },
      { id: "institution", label: "Instituição" },
      { id: "course", label: "Curso" },
      { id: "discipline", label: "Disciplina" },
      { id: "teacher", label: "Professor(a) ou orientador(a)" },
      { id: "classInfo", label: "Turma e período" },
      { id: "city", label: "Cidade e estado" },
      { id: "year", label: "Ano" },
      { id: "deliveryDate", label: "Data de entrega", placeholder: "28/09/2026" },
      { id: "area", label: "Área" },
      { id: "delimitation", label: "Tema geral e recorte específico", type: "textarea", hint: "Delimite por assunto, período, local ou grupo." , required: true },
      { id: "researchContext", label: "Contexto (onde, quando e quem)", type: "textarea", required: true },
      { id: "researchObject", label: "Objeto delimitado", type: "textarea", hint: "Expresse o tema final já com recorte e contexto.", required: true },
    ],
    checks: [
      ["paper-topic-filters", "Conferi interesse, viabilidade, relevância e competência."],
      ["paper-topic-scope", "O tema tem recorte claro e não está amplo demais."],
    ],
  },
  {
    title: "Problema de pesquisa",
    intro: "Contextualize a questão e formule uma pergunta específica, ligada ao tema e possível de investigar.",
    fields: [
      { id: "problemContext", label: "Contextualização breve do problema", type: "textarea", required: true },
      { id: "problem", label: "Pergunta de pesquisa", type: "textarea", hint: "Formule uma frase clara e termine com ponto de interrogação.", required: true },
    ],
    checks: [
      ["paper-problem-clear", "O problema é claro, específico, ligado ao tema, investigável e relevante para o Direito."],
    ],
  },
  {
    title: "Hipótese",
    intro: "Apresente uma resposta provisória ao problema. A hipótese precisa ser uma afirmação que a pesquisa possa confirmar ou refutar.",
    fields: [
      { id: "hypothesis", label: "Hipótese", type: "textarea", required: true },
    ],
    checks: [
      ["paper-hypothesis-answer", "A hipótese afirma uma resposta direta ao problema e pode ser confirmada ou refutada."],
    ],
  },
  {
    title: "Justificativa",
    intro: "Explique por que vale a pena investigar o tema, considerando sua importância jurídica, social e acadêmica e sua atualidade.",
    fields: [
      { id: "justification", label: "Justificativa", type: "textarea", size: "large", required: true },
    ],
    checks: [
      ["paper-justification-relevance", "Indiquei relevância jurídica, social ou acadêmica e atualidade do tema."],
    ],
  },
  {
    title: "Objetivos",
    intro: "O objetivo geral espelha o problema. Os objetivos específicos desdobram as etapas necessárias para alcançá-lo.",
    fields: [
      { id: "objectiveGeneral", label: "Objetivo geral", type: "textarea", hint: "Use um verbo no infinitivo.", required: true },
      { id: "objective1", label: "Objetivo específico 1", type: "textarea", required: true },
      { id: "objective2", label: "Objetivo específico 2", type: "textarea", required: true },
      { id: "objective3", label: "Objetivo específico 3 (opcional)", type: "textarea" },
    ],
    checks: [
      ["paper-objectives-aligned", "O objetivo geral corresponde ao problema e os objetivos específicos avançam em ordem lógica."],
    ],
  },
  {
    title: "Referencial teórico",
    intro: "Registre os tópicos e autores previstos e conecte cada tópico aos objetivos específicos. Priorize obras consultadas na Biblioteca Virtual FACSUR.",
    fields: [
      { id: "theory", label: "Tópicos e autores-chave previstos", type: "textarea", size: "large", hint: "Um tópico ou autor por linha.", required: true },
    ],
    checks: [
      ["paper-theory-objectives", "Cada tópico do referencial está ligado a um objetivo específico."],
      ["paper-library-priority", "Priorizei as obras disponíveis na Biblioteca Virtual FACSUR."],
    ],
  },
  {
    title: "Metodologia",
    intro: "Descreva uma metodologia compatível com o problema e os objetivos. As cinco camadas devem contar a mesma história.",
    fields: [
      { id: "methodAuthor", label: "Autor de metodologia adotado", placeholder: "Gil, Lakatos e Marconi, Prodanov e Freitas..." , required: true },
      { id: "nature", label: "Natureza", placeholder: "Básica ou aplicada", required: true },
      { id: "approach", label: "Abordagem", placeholder: "Qualitativa, quantitativa ou mista", required: true },
      { id: "ends", label: "Fins", placeholder: "Exploratória, descritiva ou explicativa", required: true },
      { id: "procedure", label: "Procedimentos", placeholder: "Bibliográfico, documental, estudo de caso...", required: true },
      { id: "instruments", label: "Instrumentos e análise dos dados", type: "textarea", required: true },
    ],
    checks: [
      ["paper-method-coherent", "As cinco camadas metodológicas estão definidas e são coerentes entre si e com os objetivos."],
    ],
  },
  {
    title: "Referências do projeto",
    intro: "Inclua apenas as fontes citadas no projeto, em ordem alfabética. Priorize a Biblioteca Virtual FACSUR e confira os dados conforme o manual.",
    custom: "sources",
    checks: [
      ["paper-project-references-only", "Incluí somente fontes citadas no texto do projeto."],
      ["paper-project-references-alpha", "Organizei as referências do projeto em ordem alfabética."],
      ["paper-project-references-library", "Conferi a prioridade das fontes da Biblioteca Virtual FACSUR."],
    ],
  },
  {
    title: "Revisão do Projeto de Paper",
    intro: "Confira o projeto, o checklist e as referências registradas antes de gerar uma cópia formatada.",
    custom: "review",
  },
];

const paperFinalStages = [
  {
    title: "Identificação, resumo e palavras-chave",
    intro: "Defina o título final e apresente um resumo informativo do trabalho, seguido pelas palavras-chave.",
    fields: [
      { id: "paperKind", label: "Etapa do trabalho", type: "select", options: [["project", "Projeto de Paper"], ["final", "Paper Final"]] },
      { id: "profile", label: "Modelo de formatação", type: "select", options: [["facsure", "Referência FACSUR"], ["livre", "Formato livre"]] },
      { id: "title", label: "Título definitivo", required: true },
      { id: "author", label: "Autor(es)", type: "textarea", hint: "Um nome por linha.", required: true },
      { id: "assignmentPrompt", label: "Proposta ou instruções do professor", type: "textarea", size: "large", hint: "Necessária para pedir uma revisão contextual por IA. O texto é enviado junto com os campos acadêmicos relevantes somente quando você solicitar." },
      { id: "institution", label: "Instituição" },
      { id: "course", label: "Curso" },
      { id: "discipline", label: "Disciplina" },
      { id: "teacher", label: "Professor(a) ou orientador(a)" },
      { id: "classInfo", label: "Turma e período" },
      { id: "city", label: "Cidade e estado" },
      { id: "year", label: "Ano" },
      { id: "deliveryDate", label: "Data de entrega", placeholder: "28/09/2026" },
      { id: "abstract", label: "Resumo", type: "textarea", size: "large", hint: "A planilha recomenda 150–250 palavras, cobrindo tema, problema, objetivo, metodologia e resultado principal.", required: true },
      { id: "keywords", label: "Palavras-chave", hint: "Use de 3 a 5 termos, separados por ponto e vírgula.", required: true },
      { id: "aiNote", label: "Nota sobre uso de IA (se exigida)", type: "textarea", hint: "Siga a política institucional e as orientações da disciplina." },
    ],
    checks: [
      ["paper-final-title", "O título é claro, conciso e delimitado."],
      ["paper-final-abstract", "O resumo cobre tema, problema, objetivo, metodologia e resultado principal."],
      ["paper-final-keywords", "Incluí de 3 a 5 palavras-chave."],
    ],
  },
  {
    title: "Introdução",
    intro: "Apresente tema, contexto, problema, hipótese, objetivos, metodologia e organização do trabalho, nesta ordem.",
    fields: [
      { id: "introduction", label: "Introdução", type: "textarea", size: "large", required: true },
    ],
    checks: [
      ["paper-final-intro-content", "A introdução apresenta tema, contexto, problema, hipótese, objetivos, metodologia e organização."],
      ["paper-final-impersonal", "Mantive redação impessoal, sem primeira pessoa."],
    ],
  },
  {
    title: "Desenvolvimento",
    intro: "Organize o desenvolvimento em tópicos com progressão argumentativa. Integre legislação, doutrina e jurisprudência; explique cada citação e apresente análise própria.",
    custom: "development",
    checks: [
      ["paper-final-development-sources", "Entrelacei legislação, doutrina e jurisprudência, em vez de separá-las em blocos."],
      ["paper-final-development-comments", "Expliquei cada citação e sua relação com o tema."],
      ["paper-final-development-analysis", "Apresentei análise própria e progressão entre parágrafos e tópicos."],
      ["paper-final-development-length", "Conferi a extensão final recomendada de 12 a 15 páginas, sem contar a capa."],
    ],
  },
  {
    title: "Conclusão",
    intro: "Retome o problema e a hipótese, sintetize o resultado e os limites da pesquisa. Não introduza fontes, dados ou assuntos novos.",
    fields: [
      { id: "conclusion", label: "Conclusão", type: "textarea", size: "large", required: true },
    ],
    checks: [
      ["paper-final-conclusion-answer", "Respondi ao problema e indiquei se a hipótese foi confirmada ou refutada."],
      ["paper-final-conclusion-no-new", "Não acrescentei assunto, autor ou dado novo e indiquei limites ou pesquisa futura."],
    ],
  },
  {
    title: "Referências finais",
    intro: "Una as fontes do projeto às novas fontes citadas no paper. Inclua somente fontes citadas, em ordem alfabética única.",
    custom: "sources",
    checks: [
      ["paper-final-references-only", "Incluí somente fontes citadas no corpo do paper."],
      ["paper-final-references-alpha", "Organizei as referências em ordem alfabética e conferi o alinhamento à esquerda."],
      ["paper-final-references-details", "Conferi autoria em caixa alta, dados bibliográficos e link, DOI e data de acesso quando disponíveis."],
      ["paper-final-references-library", "Conferi a prioridade das obras da Biblioteca Virtual FACSUR."],
      ["paper-final-formatting", "Revisei margens, fonte, espaçamento, recuo, capa e demais requisitos institucionais."],
      ["paper-final-ai-use", "Conferi a política institucional e registrei eventual uso de IA conforme as orientações da disciplina."],
    ],
  },
  {
    title: "Revisão do Paper Final",
    intro: "Confira os critérios de conteúdo e formatação antes de gerar uma cópia formatada do paper.",
    custom: "review",
  },
];

function getStages(currentProject = project) {
  if (currentProject?.projectType === "paper") {
    return currentProject.fields.paperKind === "project" ? paperProjectStages : paperFinalStages;
  }
  return caseStages;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function emptySource() {
  return {
    id: newId(),
    category: "",
    referenceType: "manual",
    details: {},
    reference: "",
    theses: [],
    cited: false,
    library: false,
  };
}

function categoryForReferenceType(type) {
  if (type === "legislation") return "legal";
  if (type === "case-law") return "case-law";
  if (type === "book" || type === "article") return "doctrine";
  return "";
}

function normalizedReferences(value) {
  return String(value ?? "")
    .split(/\n\s*\n/)
    .map((reference) => reference.trim())
    .filter(Boolean)
    .map((reference) => ({
      id: newId(),
      category: "pending",
      reference,
      theses: [],
      cited: false,
      library: false,
    }));
}

function normalizeProject(raw, legacy = false) {
  const project = emptyProject(raw?.projectType === "paper" || raw?.type === "paper" ? "paper" : "case");
  const oldFields = raw?.fields && typeof raw.fields === "object" ? raw.fields : raw;
  for (const key of Object.keys(project.fields)) {
    if (typeof oldFields?.[key] === "string") project.fields[key] = oldFields[key];
  }
  project.fields.developmentSections = Array.isArray(oldFields?.developmentSections)
    ? oldFields.developmentSections
      .filter((section) => section && typeof section === "object")
      .map((section) => ({
        id: typeof section.id === "string" ? section.id : newId(),
        title: typeof section.title === "string" ? section.title : "",
        content: typeof section.content === "string" ? section.content : "",
      }))
    : [1, 2, 3]
      .map((index) => ({
        id: newId(),
        title: typeof oldFields?.[`development${index}Title`] === "string"
          ? oldFields[`development${index}Title`]
          : "",
        content: typeof oldFields?.[`development${index}`] === "string"
          ? oldFields[`development${index}`]
          : "",
      }))
      .filter((section) => section.title || section.content);
  if (!project.fields.developmentSections.length) {
    project.fields.developmentSections = [{ id: newId(), title: "", content: "" }];
  }
  project.sources = Array.isArray(raw?.sources)
    ? raw.sources.map((source) => ({
      id: String(source.id || newId()),
      category: source.category || "",
      referenceType: referenceTypes.some(([type]) => type === source.referenceType) ? source.referenceType : "manual",
      details: source.details && typeof source.details === "object"
        ? Object.fromEntries(Object.entries(source.details).filter(([, value]) => typeof value === "string"))
        : {},
      reference: String(source.reference || ""),
      theses: Array.isArray(source.theses) ? source.theses.filter((thesis) => ["A", "B"].includes(thesis)) : [],
      cited: Boolean(source.cited),
      library: Boolean(source.library),
    }))
    : [];
  if (legacy && !project.sources.length) project.sources = normalizedReferences(oldFields?.references);
  project.criteria = Array.isArray(raw?.criteria)
    ? raw.criteria.map((item) => ({
      id: String(item.id || newId()),
      term: String(item.term || ""),
      definition: String(item.definition || ""),
      basis: String(item.basis || ""),
    }))
    : [];
  if (legacy && !project.criteria.length && typeof oldFields?.criteria === "string" && oldFields.criteria.trim()) {
    project.criteria = [{
      id: newId(),
      term: "Conteúdo do rascunho anterior",
      definition: oldFields.criteria.trim(),
      basis: "",
    }];
  }
  project.checks = raw?.checks && typeof raw.checks === "object" ? { ...raw.checks } : {};
  project.suggestedChecks = raw?.suggestedChecks && typeof raw.suggestedChecks === "object"
    ? Object.fromEntries(Object.entries(raw.suggestedChecks)
      .filter(([key, value]) => /^[a-z0-9-]{1,80}$/.test(key) && (value === true || value === "suggested" || value === "stale"))
      .map(([key, value]) => [key, value === true ? "suggested" : value]))
    : {};
  project.currentStep = Number.isInteger(raw?.currentStep)
    ? Math.max(0, Math.min(getStages(project).length - 1, raw.currentStep))
    : 0;
  project.finalized = Boolean(raw?.finalized);
  return project;
}

function loadLocalProject() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) return normalizeProject(JSON.parse(saved));
  const legacyCase = localStorage.getItem(LEGACY_STORAGE_KEY);
  const legacyPaper = localStorage.getItem(LEGACY_PAPER_STORAGE_KEY);
  const legacy = legacyCase ?? legacyPaper;
  if (!legacy) return null;
  const legacyData = JSON.parse(legacy);
  const project = normalizeProject(
    legacyCase ? legacyData : { ...legacyData, projectType: "paper" },
    true,
  );
  return project;
}

let project = null;
let accountInfo = null;
let projectRows = [];
let projectRevisions = new Map();
let projectConflict = false;
let typstModule;
let generatedSource = "";
let previewUrl = null;
let compileVersion = 0;
let storageFailure = false;
let saveError = "";
let projectAiRevision = 0;
let projectSaveTimer = null;
let projectSaveQueue = Promise.resolve();
let licenseTimer = null;
let aiAnalysisInProgress = false;
const caseChecklistAnalyses = new Map();
const caseReportAnalyses = new Map();
const caseDeepseekExplanations = new Map();
const caseAnalysisRevision = new Map();
const projectAssistantResults = new Map();
const projectAssistantConversations = new Map();
const ignoredCitationWarnings = new Set();
let activeRoute = null;

function routeHash(route) {
  if (route.view === "home" || route.view === "login") return `#/${route.view}`;
  if (route.view === "project") {
    return `#/project/${encodeURIComponent(route.id)}/step/${route.step}`;
  }
  if (route.view === "model") {
    return `#/model/${encodeURIComponent(route.id)}/step/${route.step}`;
  }
  if (route.view === "document") return `#/document/${encodeURIComponent(route.id)}`;
  return "#/home";
}

function parseRouteHash() {
  let segments;
  try {
    segments = window.location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  } catch {
    return null;
  }
  if (segments.length === 1 && ["home", "login"].includes(segments[0])) {
    return { view: segments[0] };
  }
  if (segments[0] === "project" && segments.length === 4 && segments[2] === "step") {
    const step = Number(segments[3]);
    if (segments[1] && Number.isInteger(step) && step >= 0) {
      return { view: "project", id: segments[1], step };
    }
  }
  if (segments[0] === "model" && segments.length === 4 && segments[2] === "step") {
    const step = Number(segments[3]);
    if (segments[1] && Number.isInteger(step) && step >= 0) {
      return { view: "model", id: segments[1], step };
    }
  }
  if (segments[0] === "document" && segments.length === 2 && segments[1]) {
    return { view: "document", id: segments[1] };
  }
  return null;
}

function routeFromLocation() {
  const route = parseRouteHash();
  if (!route) return null;
  const state = window.history.state;
  if (!state?.roteiroRoute || routeHash(state.roteiroRoute) !== window.location.hash) return route;
  return {
    ...route,
    historyIndex: Number.isInteger(state.roteiroHistoryIndex) ? state.roteiroHistoryIndex : 0,
    returnHistoryIndex: Number.isInteger(state.roteiroReturnHistoryIndex)
      ? state.roteiroReturnHistoryIndex
      : null,
  };
}

function syncAppRoute(route, mode = "replace") {
  const hash = routeHash(route);
  const effectiveMode = mode === "push" && window.location.hash !== hash ? "push" : "replace";
  const currentIndex = Number.isInteger(window.history.state?.roteiroHistoryIndex)
    ? window.history.state.roteiroHistoryIndex
    : activeRoute?.historyIndex ?? 0;
  const historyIndex = effectiveMode === "push" ? currentIndex + 1 : route.historyIndex ?? currentIndex;
  const returnHistoryIndex = route.view === "model" || route.view === "document"
    ? route.returnHistoryIndex
      ?? (activeRoute?.view === "project" ? activeRoute.historyIndex : activeRoute?.returnHistoryIndex)
      ?? null
    : null;
  const state = {
    ...window.history.state,
    roteiroRoute: { view: route.view, id: route.id, step: route.step },
    roteiroHistoryIndex: historyIndex,
    roteiroReturnHistoryIndex: returnHistoryIndex,
  };
  window.history[`${effectiveMode}State`](state, "", hash);
  activeRoute = { ...route, historyIndex, returnHistoryIndex };
}

function exitModelToProject(fallback) {
  const distance = activeRoute?.historyIndex - activeRoute?.returnHistoryIndex;
  if (Number.isInteger(distance) && distance > 0) {
    window.history.go(-distance);
    return;
  }
  fallback();
}

async function restoreAppRoute(route) {
  const previousRoute = activeRoute;
  const leavingProject = project?.id
    && !(route.view === "project" && route.id === project.id);
  if (leavingProject) {
    if (projectConflict && !window.confirm(
      "Há alterações locais em conflito que não foram salvas. Baixe uma cópia JSON antes de sair, se precisar preservá-las. Continuar?",
    )) {
      if (previousRoute) syncAppRoute(previousRoute);
      showWorkflow("A navegação foi cancelada para preservar as alterações locais.");
      return;
    }
    if (!await flushProjectSave()) {
      if (previousRoute) syncAppRoute(previousRoute);
      showWorkflow("O último salvamento não foi confirmado. A tela atual foi mantida para evitar perder alterações.");
      return;
    }
  }

  if (route.view === "login") {
    showLogin();
    return;
  }
  if (route.view === "home") {
    project = null;
    showLanding();
    return;
  }
  if (route.view === "project") {
    if (project?.id === route.id) {
      const step = Math.min(route.step, getStages().length - 1);
      if (project.currentStep !== step) {
        project.currentStep = step;
        saveProject();
      }
      showWorkflow();
      return;
    }
    await openRemoteProject(route.id, "replace", route.step);
    return;
  }

  const model = reportModels.find((item) => item.id === route.id);
  if (!model) {
    showLanding("O modelo solicitado não está disponível.");
    return;
  }
  if (route.view === "model") {
    showModelWorkflow(model, Boolean(project), route.step, "replace", route.returnHistoryIndex);
    return;
  }
  if (route.view === "document") {
    showModelDocument(model, Boolean(project), null, "replace", route.returnHistoryIndex);
    return;
  }
  showLanding();
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    if (response.ok) throw new Error("O servidor retornou uma resposta inválida.");
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/login") {
      accountInfo = null;
      clearTimeout(licenseTimer);
    }
    const error = new Error(payload.message || "Não foi possível concluir a operação.");
    error.code = payload.error || "request_failed";
    error.status = response.status;
    throw error;
  }
  return payload;
}

function licenseIsActive() {
  return Boolean(accountInfo?.active);
}

function canEditProject() {
  return licenseIsActive() && !projectConflict;
}

function formatDate(timestamp) {
  if (!timestamp) return "ainda não ativada";
  return new Date(timestamp * 1000).toLocaleDateString("pt-BR");
}

function analysisQuotaLabel() {
  return accountInfo?.unlimited
    ? "ilimitadas"
    : `${accountInfo?.ai_analysis_remaining ?? 0} restantes`;
}

function analysisQuotaConfirmation() {
  return accountInfo?.unlimited
    ? "Esta solicitação pode gerar custo na infraestrutura de análise."
    : `Consome 1 de ${accountInfo.ai_analysis_limit} análises da licença, mesmo se falhar.`;
}

function deepseekQuotaLabel() {
  return accountInfo?.unlimited
    ? "ilimitadas"
    : `${accountInfo?.deepseek_explanation_remaining ?? 0} chamadas restantes`;
}

function deepseekQuotaConfirmation() {
  return accountInfo?.unlimited
    ? "Esta solicitação pode gerar custo na infraestrutura de assistência."
    : `Consome 1 de ${accountInfo.deepseek_explanation_limit} chamadas de assistência da licença, mesmo se falhar.`;
}

function scheduleLicenseExpiry() {
  clearTimeout(licenseTimer);
  if (!accountInfo?.active || accountInfo.unlimited || !accountInfo.expires_at) return;
  const delay = accountInfo.expires_at * 1000 - Date.now();
  if (delay <= 0) {
    accountInfo.active = false;
    if (project) showWorkflow("A licença venceu. O projeto permanece disponível para leitura e exportação.");
    else showLanding();
    return;
  }
  licenseTimer = setTimeout(() => {
    if (!accountInfo) return;
    if (accountInfo?.expires_at * 1000 > Date.now()) {
      scheduleLicenseExpiry();
      return;
    }
    accountInfo.active = false;
    if (project) showWorkflow("A licença venceu. O projeto permanece disponível para leitura e exportação.");
    else showLanding();
  }, Math.min(delay + 50, 2_147_000_000));
}

async function refreshAccount() {
  const result = await apiRequest("/session");
  accountInfo = result.account;
  scheduleLicenseExpiry();
  projectRows = (await apiRequest("/projects")).projects;
}

async function refreshProjects() {
  projectRows = (await apiRequest("/projects")).projects;
}

async function loginWithCode(code) {
  const result = await apiRequest("/login", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  accountInfo = result.account;
  scheduleLicenseExpiry();
  await refreshProjects();
}

async function logout() {
  if (!await flushProjectSave()) {
    throw new Error("O último salvamento não foi confirmado. A sessão continua aberta para evitar perder alterações.");
  }
  await apiRequest("/logout", { method: "POST", body: "{}" });
  clearTimeout(licenseTimer);
  accountInfo = null;
  projectRows = [];
  project = null;
  projectRevisions.clear();
  projectConflict = false;
  showLogin();
}

async function createRemoteProject(projectType, initialProject = emptyProject(projectType)) {
  if (!licenseIsActive()) {
    showLanding("A licença venceu. Os projetos continuam disponíveis para leitura e exportação, mas não podem ser criados ou editados.");
    return;
  }
  try {
    const result = await apiRequest("/projects", {
      method: "POST",
      body: JSON.stringify({ project: initialProject }),
    });
    await refreshAccount();
    await openRemoteProject(result.id);
  } catch (error) {
    if (error.code === "project_limit") await refreshAccount();
    showLanding(error.message);
  }
}

async function openRemoteProject(id, historyMode = "push", step = null) {
  clearTimeout(projectSaveTimer);
  try {
    const result = await apiRequest(`/projects/${encodeURIComponent(id)}`);
    project = normalizeProject(result.project);
    project.id = result.id;
    clearCaseAiResults(result.id);
    if (Number.isInteger(step)) project.currentStep = Math.min(step, getStages().length - 1);
    projectRevisions.set(result.id, result.revision);
    projectConflict = false;
    saveError = "";
    showWorkflow("", historyMode);
    return true;
  } catch (error) {
    showLanding(error.message);
    return false;
  }
}

function saveProject() {
  if (!project?.id || !canEditProject()) return false;
  clearTimeout(projectSaveTimer);
  const id = project.id;
  const snapshot = JSON.stringify(project);
  const note = document.querySelector("#save-note");
  if (note) note.textContent = "Salvando no servidor…";
  projectSaveTimer = setTimeout(() => {
    queueProjectSave(id, snapshot);
  }, 450);
  return true;
}

function queueProjectSave(id, snapshot) {
  projectSaveQueue = projectSaveQueue.catch(() => {}).then(async () => {
    if (projectConflict) return false;
    try {
      const result = await apiRequest(`/projects/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify({ project: JSON.parse(snapshot), revision: projectRevisions.get(id) }),
      });
      projectRevisions.set(id, result.revision);
      if (project?.id === id) {
        saveError = "";
        const saveNote = document.querySelector("#save-note");
        if (saveNote) saveNote.textContent = "Salvo na conta";
      }
      return true;
    } catch (error) {
      if (project?.id === id) {
        saveError = error.message;
        const saveNote = document.querySelector("#save-note");
        if (saveNote) saveNote.textContent = `Falha ao salvar: ${error.message}`;
        if (error.code === "license_expired") {
          accountInfo.active = false;
          showWorkflow("A licença venceu. O projeto foi preservado no servidor e está disponível para leitura e exportação.");
        } else if (error.code === "project_conflict") {
          projectConflict = true;
          showWorkflow("Outra sessão salvou uma versão mais recente. Baixe uma cópia JSON deste rascunho, se precisar preservá-lo, e reabra a versão do servidor antes de continuar.");
        }
      }
      return false;
    }
  });
  return projectSaveQueue;
}

async function flushProjectSave() {
  clearTimeout(projectSaveTimer);
  if (projectConflict) {
    await projectSaveQueue.catch(() => {});
    return true;
  }
  if (project?.id && canEditProject()) {
    return queueProjectSave(project.id, JSON.stringify(project));
  }
  await projectSaveQueue.catch(() => {});
  return true;
}

function getSourceCounts() {
  const sources = project.sources;
  const doctrine = sources.filter((source) => source.category === "doctrine");
  const doctrinesFor = (thesis) => doctrine.filter((source) => source.library && source.theses.includes(thesis)).length;
  const categoryFor = (category, thesis) => sources.filter((source) => source.category === category && source.theses.includes(thesis)).length;
  const uniqueDoctrine = new Set(doctrine.filter((source) => source.library).map((source) => source.reference.trim().toLocaleLowerCase("pt-BR")));
  return {
    libraryTotal: uniqueDoctrine.size,
    doctrineTotal: uniqueDoctrine.size,
    doctrineA: doctrinesFor("A"),
    doctrineB: doctrinesFor("B"),
    legalA: categoryFor("legal", "A"),
    legalB: categoryFor("legal", "B"),
    caseA: categoryFor("case-law", "A"),
    caseB: categoryFor("case-law", "B"),
  };
}

function getSourceRules() {
  const counts = getSourceCounts();
  const paper = project.projectType === "paper";
  const sourceRowsComplete = project.sources.length > 0 && project.sources.every((source) =>
    sourceTypes.some(([category]) => category === source.category)
      && source.reference.trim() && (paper || source.theses.length) && source.cited);
  const normalized = project.sources.map((source) => source.reference.trim().toLocaleLowerCase("pt-BR"));
  const noDuplicates = normalized.length === new Set(normalized).size;
  if (paper) {
    return [
      { label: "Todas as fontes estão classificadas, completas e foram citadas no texto", done: sourceRowsComplete },
      { label: "Sem referências duplicadas na lista", done: project.sources.length > 0 && noDuplicates },
    ];
  }
  return [
    { label: "Quatro obras doutrinárias distintas da Biblioteca Virtual FACSUR", done: counts.doctrineTotal >= 4 },
    { label: "Pelo menos duas dessas obras vinculadas à tese A", done: counts.doctrineA >= 2 },
    { label: "Pelo menos duas dessas obras vinculadas à tese B", done: counts.doctrineB >= 2 },
    { label: "Fonte legal vinculada a cada tese", done: counts.legalA > 0 && counts.legalB > 0 },
    { label: "Fonte jurisprudencial vinculada a cada tese", done: counts.caseA > 0 && counts.caseB > 0 },
    { label: "Todas as fontes classificadas, ligadas a tese(s) e marcadas como citadas", done: sourceRowsComplete },
    { label: "Sem referências duplicadas na lista", done: project.sources.length > 0 && noDuplicates },
  ];
}

function getRequirements() {
  const requirements = [];
  const stages = getStages();
  for (let index = 0; index < stages.length - 1; index += 1) {
    const stage = stages[index];
    for (const field of stage.fields ?? []) {
      if (field.required) {
        requirements.push({
          step: index,
          label: `${field.label} preenchido`,
          done: Boolean(String(project.fields[field.id] ?? "").trim()),
        });
      }
    }
    if (stage.fields?.some((field) => field.id === "abstract")) {
      const words = String(project.fields.abstract ?? "").trim().split(/\s+/).filter(Boolean).length;
      requirements.push({
        step: index,
        label: `Resumo entre 150 e 250 palavras (${words} no momento)`,
        done: words >= 150 && words <= 250,
      });
    }
    for (const [key, label] of stage.checks ?? []) {
      requirements.push({ step: index, label, done: Boolean(project.checks[key]) });
    }
    if (stage.custom === "criteria") {
      const complete = project.criteria.length > 0 && project.criteria.every((item) =>
        item.term.trim() && item.definition.trim() && item.basis.trim());
      requirements.push({ step: index, label: "Glossário com conceito, definição e fundamento", done: complete });
    }
    if (stage.custom === "sources") {
      for (const rule of getSourceRules()) requirements.push({ step: index, ...rule });
    }
    if (stage.custom === "development") {
      for (const [sectionIndex, section] of project.fields.developmentSections.entries()) {
        if (sectionIndex === 0 || section.title.trim() || section.content.trim()) {
          requirements.push({
            step: index,
            label: `Título do tópico ${sectionIndex + 1} preenchido`,
            done: Boolean(section.title.trim()),
          });
          requirements.push({
            step: index,
            label: `Texto do tópico ${sectionIndex + 1} preenchido`,
            done: Boolean(section.content.trim()),
          });
        }
      }
    }
  }
  return requirements;
}

function getProgress() {
  const requirements = getRequirements();
  const done = requirements.filter((requirement) => requirement.done).length;
  return { done, total: requirements.length, percent: requirements.length ? Math.round((done / requirements.length) * 100) : 0 };
}

function stageComplete(index) {
  const stages = getStages();
  if (index === stages.length - 1) return allRequirementsComplete();
  const requirements = getRequirements().filter((requirement) => requirement.step === index);
  return requirements.length > 0 && requirements.every((requirement) => requirement.done);
}

function allRequirementsComplete() {
  const requirements = getRequirements();
  return requirements.length > 0 && requirements.every((requirement) => requirement.done);
}

function addTopbar() {
  app.innerHTML = `
    <header class="topbar">
      <div class="brand">roteiro</div>
      <div class="topbar-actions">
        <div class="topnote">${accountInfo ? accountInfo.unlimited ? "Acesso do proprietário · ilimitado" : `Licença até ${formatDate(accountInfo.expires_at)}` : "Escrita acadêmica · Direito"}</div>
        ${accountInfo ? '<button class="text-button" type="button" id="logout-button">Sair</button>' : ""}
      </div>
    </header>
    <main class="shell" id="main"></main>`;
  document.querySelector("#logout-button")?.addEventListener("click", async () => {
    try {
      await logout();
    } catch (error) {
      const message = `Não foi possível encerrar a sessão: ${error.message}`;
      if (project) showWorkflow(message);
      else showLanding(message);
    }
  });
}

function showLogin(message = "", historyMode = "replace") {
  clearTimeout(licenseTimer);
  accountInfo = null;
  projectRows = [];
  project = null;
  projectRevisions.clear();
  projectConflict = false;
  syncAppRoute({ view: "login" }, historyMode);
  addTopbar();
  const main = document.querySelector("#main");
  main.className = "shell login-shell";
  main.innerHTML = `
    <section class="landing login-panel" aria-labelledby="login-title">
      <p class="eyebrow">Acesso por código</p>
      <h1 id="login-title">Entre no seu roteiro.</h1>
      <p class="lede">Use o código recebido para abrir sua conta e acessar seus projetos.</p>
      ${message ? `<p class="notice" role="alert">${escapeHtml(message)}</p>` : ""}
      <div class="notice privacy-notice">
        <strong>Sobre seus dados:</strong> a conta não pede nome, e-mail ou senha, mas os projetos,
        incluindo o nome do aluno e o conteúdo que você preencher, ficam armazenados no servidor
        associados ao código. Ao vencer a licença, eles permanecem guardados e disponíveis para
        leitura e exportação; novas edições exigem renovação. Para solicitar acesso, correção ou
        remoção, fale com quem entregou seu código. Mantenha o código em segredo.
      </div>
      <form id="login-form" class="login-form">
        <label for="access-code">Código de acesso</label>
        <input id="access-code" name="code" type="text" autocomplete="one-time-code" autocapitalize="characters" spellcheck="false" required>
        <button class="button button-primary" type="submit">Entrar</button>
        <p class="field-hint" id="login-status">A conta não pede nome, e-mail ou senha. Guarde seu código: ele é a chave de acesso.</p>
      </form>
      <p class="privacy-note">Seus projetos ficam associados à conta no servidor. Não compartilhe seu código com outras pessoas.</p>
    </section>`;
  document.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const codeInput = form.elements.code;
    const button = form.querySelector("button[type=submit]");
    const status = document.querySelector("#login-status");
    button.disabled = true;
    status.textContent = "Validando código…";
    try {
      await loginWithCode(codeInput.value);
      codeInput.value = "";
      showLanding();
    } catch (error) {
      status.textContent = error.message;
      button.disabled = false;
      codeInput.focus();
    }
  });
}

function renderModelField(field, model) {
  const id = `model-field-${field.id}`;
  const value = model.workflow.fields[field.id] ?? "";
  const help = field.id === "abstract"
    ? `${String(value).trim().split(/\s+/).filter(Boolean).length} palavras (recomendação: 150–250).`
    : field.hint ?? "";
  const hint = help ? `<p class="field-hint" id="${id}-hint">${escapeHtml(help)}</p>` : "";
  let control;
  if (field.type === "textarea") {
    control = `<textarea id="${id}" name="${field.id}" data-size="${field.size ?? ""}" readonly aria-readonly="true" ${help ? `aria-describedby="${id}-hint"` : ""}>${escapeHtml(value)}</textarea>`;
  } else if (field.type === "select") {
    control = `<select id="${id}" name="${field.id}" disabled aria-readonly="true">
      ${field.options.map(([option, label]) => `<option value="${escapeHtml(option)}" ${value === option ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}
    </select>`;
  } else {
    control = `<input id="${id}" name="${field.id}" type="text" value="${escapeHtml(value)}" readonly aria-readonly="true" ${field.placeholder ? `placeholder="${escapeHtml(field.placeholder)}"` : ""} ${help ? `aria-describedby="${id}-hint"` : ""}>`;
  }
  return `<div class="field model-field">
    <div class="field-label-row"><label for="${id}">${escapeHtml(field.label)}${field.required ? " *" : ""}</label>${field.required ? '<span class="field-state is-required">Obrigatório</span>' : ""}</div>
    ${control}
    ${hint}
  </div>`;
}

function renderModelCriteria(model) {
  return `<div class="field-group model-readonly-section">
    <h3>Critérios e valores</h3>
    <p class="field-hint">Este conteúdo aparece na seção correspondente do relatório.</p>
    <div class="field"><label for="model-criteria-text">Texto do modelo</label><textarea id="model-criteria-text" data-size="large" readonly aria-readonly="true">${escapeHtml(model.workflow.fields.criteriaText)}</textarea></div>
  </div>`;
}

function renderModelSources(model) {
  return `<div class="field-group model-readonly-section">
    <h3>Controle de fontes</h3>
    <p class="field-hint">Estas são as referências listadas no relatório. Os rótulos mostram a categoria atribuída para orientar a organização.</p>
    <div class="source-list">
      ${model.workflow.sources.map((source, index) => `
        <article class="source-row model-source-row">
          <div class="source-row-head"><strong>Fonte ${index + 1} · ${escapeHtml(sourceTypes.find(([category]) => category === source.category)?.[1] ?? "Fonte")}</strong><span class="model-source-status">Citadas no relatório</span></div>
          <p class="model-source-reference">${escapeHtml(source.reference)}</p>
        </article>`).join("")}
    </div>
    <section class="model-citation-examples" aria-labelledby="model-citation-examples-title">
      <h3 id="model-citation-examples-title">Como as citações aparecem no texto</h3>
      <ul>
        ${(model.citations ?? []).map((citation) => `<li><span>${escapeHtml(citation.type)}</span><p>${escapeHtml(citation.text)}</p></li>`).join("")}
      </ul>
    </section>
  </div>`;
}

function getModelPdfUrl(model) {
  if (model.pdfUrl) return model.pdfUrl;
  return model.pdfDataAttribute ? document.body.dataset[model.pdfDataAttribute] ?? "" : "";
}

function renderModelChecks(stage) {
  if (!stage.checks?.length) return "";
  return `<fieldset class="stage-checklist model-checklist" disabled>
    <legend>Checklist desta etapa</legend>
    ${stage.checks.map(([, label]) => `
      <label class="check-item">
        <input type="checkbox" disabled>
        <span>${escapeHtml(label)}</span>
      </label>`).join("")}
    <p class="field-hint">Os checklists são autoavaliações da ferramenta, não fazem parte do relatório original e permanecem desmarcados neste exemplo.</p>
  </fieldset>`;
}

function showModelWorkflow(model, returnToWorkflow = false, index = 0, historyMode = "replace", returnHistoryIndex = null) {
  const stages = getStages(model.workflow);
  const stageIndex = Math.max(0, Math.min(index, stages.length - 1));
  const stage = stages[stageIndex];
  const route = { view: "model", id: model.id, step: stageIndex };
  if (returnToWorkflow && Number.isInteger(returnHistoryIndex)) {
    route.returnHistoryIndex = returnHistoryIndex;
  } else if (returnToWorkflow && activeRoute?.view === "project") {
    route.returnHistoryIndex = activeRoute.historyIndex;
  } else if (returnToWorkflow) {
    route.returnHistoryIndex = activeRoute?.returnHistoryIndex;
  }
  syncAppRoute(route, historyMode);
  addTopbar();
  const main = document.querySelector("#main");
  const pdfUrl = getModelPdfUrl(model);
  main.className = "shell app-shell model-workflow-shell";
  main.innerHTML = `
    <div class="app-heading">
      <div>
        <p class="eyebrow">Demonstração preenchida · Somente leitura</p>
        <h1>${escapeHtml(model.title)}</h1>
      </div>
      <div class="app-heading-actions">
        <button class="back-link" type="button" id="model-view-document">Ler trabalho completo</button>
        <button class="back-link" type="button" id="model-exit">← ${returnToWorkflow ? "Voltar ao projeto" : "Início"}</button>
      </div>
    </div>
    <div class="model-readonly-note">Os campos mostram o exemplo nesta etapa do roteiro. Você pode navegar, mas não editar nem salvar o conteúdo; seu projeto permanece intacto.</div>
    <div class="workspace">
      <nav class="step-nav" aria-label="Etapas do modelo preenchido">
        ${stages.map((item, step) => `
          <button class="step-link" type="button" data-model-step="${step}" aria-current="${step === stageIndex ? "step" : "false"}">
            <span class="step-index">${String(step + 1).padStart(2, "0")}</span>
            <span>${escapeHtml(item.title)}</span>
          </button>`).join("")}
      </nav>
      <section class="step-card" aria-labelledby="model-step-title">
        <p class="step-count">ETAPA ${String(stageIndex + 1).padStart(2, "0")} DE ${String(stages.length).padStart(2, "0")}</p>
        <h2 id="model-step-title">${escapeHtml(stage.title)}</h2>
        <p class="step-intro">${escapeHtml(stage.intro)}</p>
        ${stage.fields?.length ? `<div class="form-grid model-fields">${stage.fields.map((field) => renderModelField(field, model)).join("")}</div>` : ""}
        ${stage.custom === "criteria" ? renderModelCriteria(model) : ""}
        ${stage.custom === "sources" ? renderModelSources(model) : ""}
        ${stage.custom === "review" ? `
          <div class="model-review">
            <h3>O relatório de exemplo está pronto para consulta</h3>
            <p>Confira o trabalho completo ou abra o arquivo original em PDF. Esta demonstração não altera o projeto que está salvo no navegador.</p>
            <button class="button button-primary" type="button" id="model-review-document">Ler trabalho completo</button>
            ${pdfUrl ? `<a class="button" href="${escapeHtml(pdfUrl)}" target="_blank" rel="noopener noreferrer">Abrir PDF integral ↗</a>` : ""}
          </div>` : ""}
        ${renderModelChecks(stage)}
        <div class="step-actions">
          <button class="button" type="button" id="model-previous" ${stageIndex === 0 ? "disabled" : ""}>Anterior</button>
          <span class="save-note">Demonstração · não salva</span>
          <button class="button button-primary" type="button" id="model-next" ${stageIndex === stages.length - 1 ? "disabled" : ""}>Próxima etapa</button>
        </div>
      </section>
    </div>`;
  document.querySelector("#model-exit").addEventListener("click", () => {
    if (returnToWorkflow && project) exitModelToProject(() => showWorkflow("", "push"));
    else showLanding("", "push");
  });
  document.querySelector("#model-view-document").addEventListener("click", () => {
    showModelDocument(model, returnToWorkflow, () => showModelWorkflow(model, returnToWorkflow, stageIndex), "push");
  });
  document.querySelector("#model-review-document")?.addEventListener("click", () => {
    showModelDocument(model, returnToWorkflow, () => showModelWorkflow(model, returnToWorkflow, stageIndex), "push");
  });
  document.querySelectorAll("[data-model-step]").forEach((button) => {
    button.addEventListener("click", () => showModelWorkflow(model, returnToWorkflow, Number(button.dataset.modelStep), "push"));
  });
  document.querySelector("#model-previous").addEventListener("click", () => showModelWorkflow(model, returnToWorkflow, stageIndex - 1, "push"));
  document.querySelector("#model-next").addEventListener("click", () => showModelWorkflow(model, returnToWorkflow, stageIndex + 1, "push"));
}

function showModelDocument(model, returnToWorkflow = false, returnFromDocument = null, historyMode = "replace", returnHistoryIndex = null) {
  syncAppRoute({
    view: "document",
    id: model.id,
    returnHistoryIndex: returnHistoryIndex
      ?? (returnToWorkflow
        ? activeRoute?.view === "project"
          ? activeRoute.historyIndex
          : activeRoute?.returnHistoryIndex
        : null),
  }, historyMode);
  addTopbar();
  const main = document.querySelector("#main");
  const pdfUrl = getModelPdfUrl(model);
  main.className = "shell model-shell";
  main.innerHTML = `
    <div class="app-heading">
      <div>
        <p class="eyebrow">Trabalho completo · Modelo de consulta</p>
        <h1>${escapeHtml(model.title)}</h1>
      </div>
      <div class="app-heading-actions">
        <button class="back-link" type="button" id="model-view-workflow">Ver roteiro preenchido</button>
        <button class="back-link" type="button" id="model-back">← ${returnToWorkflow ? "Voltar ao projeto" : "Início"}</button>
      </div>
    </div>
    <div class="model-toolbar">
      <p>Leia o trabalho completo ou abra o PDF original. Esta consulta não altera nem substitui o projeto salvo.</p>
      ${pdfUrl ? `<a class="button button-primary" href="${escapeHtml(pdfUrl)}" target="_blank" rel="noopener noreferrer">Abrir relatório integral em PDF ↗</a>` : ""}
    </div>
    <article class="model-document" aria-labelledby="model-document-title">
      <header class="model-cover">
        <p class="model-institution">${escapeHtml(model.institution || model.workflow.fields.institution)}<br>Curso de ${escapeHtml(model.course || model.workflow.fields.course)}</p>
        <h2 id="model-document-title">${escapeHtml(model.title)}</h2>
        <p>${escapeHtml(model.authors).replace(/\n/g, "<br>")}</p>
        <dl class="model-metadata">
          <div><dt>Disciplina</dt><dd>${escapeHtml(model.discipline)}</dd></div>
          <div><dt>Professor(a)</dt><dd>${escapeHtml(model.teacher)}</dd></div>
          <div><dt>Turma</dt><dd>${escapeHtml(model.classInfo)}</dd></div>
          <div><dt>Entrega</dt><dd>${escapeHtml(model.deliveryDate)}</dd></div>
          <div><dt>Local e ano</dt><dd>${escapeHtml(model.city)} · ${escapeHtml(model.year)}</dd></div>
        </dl>
      </header>
      <div class="model-content">
        ${model.sections.map((section) => `
          <section class="model-section">
            <h2>${escapeHtml(section.title)}</h2>
            ${section.paragraphs.map((paragraph) => typeof paragraph === "string"
    ? `<p>${escapeHtml(paragraph)}</p>`
    : `<blockquote>${escapeHtml(paragraph.quote)}</blockquote>`).join("")}
          </section>`).join("")}
        <section class="model-section model-citations" aria-labelledby="model-citations-title">
          <h2 id="model-citations-title">Exemplos de citações presentes no relatório</h2>
          <ul>
            ${(model.citations ?? []).map((citation) => `
              <li><span>${escapeHtml(citation.type)}</span><p>${escapeHtml(citation.text)}</p></li>`).join("")}
          </ul>
        </section>
        <section class="model-section model-references" aria-labelledby="model-references-title">
          <h2 id="model-references-title">Referências do exemplo</h2>
          <p class="model-reference-note">As fontes abaixo reproduzem a lista do relatório, em ordem alfabética única. A etiqueta indica a categoria de cada fonte.</p>
          <ol class="model-source-list">
            ${model.sources.map((source) => `<li><span>${escapeHtml(source.category)}</span><p>${escapeHtml(source.reference)}</p></li>`).join("")}
          </ol>
        </section>
        <p class="model-disclaimer">Este é um exemplo acadêmico para consulta, não um modelo de resposta jurídica. Confira as normas e orientações atuais da disciplina antes de elaborar seu trabalho.</p>
      </div>
    </article>`;
  document.querySelector("#model-back").addEventListener("click", () => {
    if (returnFromDocument) returnFromDocument();
    else if (returnToWorkflow && project) exitModelToProject(() => showWorkflow("", "push"));
    else showLanding("", "push");
  });
  document.querySelector("#model-view-workflow").addEventListener("click", () => showModelWorkflow(model, returnToWorkflow, 0, "push"));
}

function showLegacyLanding(message = "") {
  addTopbar();
  const main = document.querySelector("#main");
  main.className = "shell landing-shell";
  const progress = project ? getProgress() : null;
  const otherWorkflow = project?.projectType === "paper" ? "Relatório de case jurídico" : "Paper jurídico";
  main.innerHTML = `
    <section class="landing" aria-labelledby="page-title">
      <p class="eyebrow">Trabalhos acadêmicos · Direito</p>
      <h1 id="page-title">${project ? "Continue seu trabalho." : "Escolha o tipo de trabalho."}</h1>
      <p class="lede">Orientações passo a passo para você construir seu texto com autonomia. Seu projeto fica salvo neste navegador.</p>
      ${message ? `<p class="notice" role="alert">${escapeHtml(message)}</p>` : ""}
      <div class="workflow-catalog">
        <section class="workflow-card ${project?.projectType === "paper" ? "workflow-card-disabled" : ""}" aria-labelledby="case-workflow-title">
          <div class="workflow-card-copy">
            <p class="eyebrow">${project?.projectType === "case" ? "Projeto atual" : project ? "Outro formato" : "Roteiro disponível"}</p>
            <h2 id="case-workflow-title">Relatório de case jurídico</h2>
            <p>Desenvolva as seções do relatório, acompanhe seu progresso e organize as fontes consultadas.</p>
          </div>
          ${project?.projectType === "case" ? `
          <div class="project-resume">
          <div>
            <h3>${escapeHtml(project.fields.title || "Relatório sem título")}</h3>
            <p class="progress-summary">${progress.done} de ${progress.total} requisitos atendidos · ${progress.percent}%</p>
            ${renderProgressBar(progress)}
          </div>
          <div class="project-controls">
            <button class="button button-primary" type="button" id="resume-project">Continuar relatório</button>
            <button class="text-button" type="button" id="restart-project" ${storageFailure ? "disabled" : ""}>Começar outro relatório</button>
          </div>
          </div>` : project ? `<button class="button" type="button" data-start-type="case" ${storageFailure ? "disabled" : ""}>Selecionar ${escapeHtml(otherWorkflow)} <span aria-hidden="true">→</span></button>` : `
          <button class="button button-primary start-button" type="button" id="start-project" ${storageFailure ? "disabled" : ""}>Começar relatório <span aria-hidden="true">→</span></button>`}
        </section>
        <section class="workflow-card ${project?.projectType === "paper" ? "" : "workflow-card-disabled"}" aria-labelledby="paper-workflow-title">
          <div class="workflow-card-copy">
            <p class="eyebrow">${project?.projectType === "paper" ? "Projeto atual" : project ? "Outro formato" : "Roteiro disponível"}</p>
            <h2 id="paper-workflow-title">Paper jurídico</h2>
            <p>Planeje o projeto de pesquisa ou desenvolva o paper final.</p>
          </div>
          ${project?.projectType === "paper" ? `
          <div class="project-resume">
          <div>
            <h3>${escapeHtml(project.fields.title || "Paper sem título")}</h3>
            <p class="progress-summary">${progress.done} de ${progress.total} requisitos atendidos · ${progress.percent}%</p>
            ${renderProgressBar(progress)}
          </div>
          <div class="project-controls">
            <button class="button button-primary" type="button" id="resume-project">Continuar Paper</button>
            <button class="text-button" type="button" id="restart-project" ${storageFailure ? "disabled" : ""}>Começar outro paper</button>
          </div>
          </div>` : project ? `<button class="button" type="button" data-start-type="paper" ${storageFailure ? "disabled" : ""}>Selecionar ${escapeHtml(otherWorkflow)} <span aria-hidden="true">→</span></button>` : `
          <button class="button button-primary start-button" type="button" id="start-paper" ${storageFailure ? "disabled" : ""}>Começar paper <span aria-hidden="true">→</span></button>`}
        </section>
      </div>
      ${reportModels.map((model) => `
        <section class="model-entry" aria-labelledby="model-entry-${escapeHtml(model.id)}">
          <div>
            <p class="eyebrow">${escapeHtml(model.typeLabel)}</p>
            <h2 id="model-entry-${escapeHtml(model.id)}">${escapeHtml(model.title)}</h2>
            <p>Explore o roteiro com os campos preenchidos e consulte a apresentação completa do trabalho.</p>
          </div>
          <div class="model-entry-actions">
            <button class="button button-primary" type="button" data-model-workflow="${escapeHtml(model.id)}">Ver preenchido</button>
            <button class="button" type="button" data-model-document="${escapeHtml(model.id)}">Ler trabalho completo</button>
          </div>
        </section>`).join("")}
      <div class="notice">O indicador confere campos, autoavaliações e registro das fontes; não verifica a correção jurídica do conteúdo. O relatório não é enviado a um servidor.</div>
    </section>`;
  document.querySelector("#start-project")?.addEventListener("click", () => {
    project = emptyProject("case");
    const saved = saveProject();
    showWorkflow(saved ? "" : saveError);
  });
  document.querySelector("#start-paper")?.addEventListener("click", () => {
    project = emptyProject("paper");
    const saved = saveProject();
    showWorkflow(saved ? "" : saveError);
  });
  document.querySelector("#resume-project")?.addEventListener("click", () => showWorkflow());
  document.querySelectorAll("[data-model-workflow]").forEach((button) => {
    button.addEventListener("click", () => {
      const model = reportModels.find((item) => item.id === button.dataset.modelWorkflow);
      if (model) showModelWorkflow(model);
    });
  });
  document.querySelectorAll("[data-model-document]").forEach((button) => {
    button.addEventListener("click", () => {
      const model = reportModels.find((item) => item.id === button.dataset.modelDocument);
      if (model) showModelDocument(model);
    });
  });
  document.querySelector("#restart-project")?.addEventListener("click", () => {
    const replacement = emptyProject(project.projectType);
    if (!window.confirm("Começar outro trabalho substituirá o único projeto salvo neste navegador. Deseja continuar?")) return;
    project = replacement;
    const saved = saveProject();
    showWorkflow(saved ? "" : saveError);
  });
  document.querySelectorAll("[data-start-type]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!window.confirm("Selecionar outro tipo de trabalho substituirá o projeto salvo neste navegador. Deseja continuar?")) return;
      project = emptyProject(button.dataset.startType);
      const saved = saveProject();
      showWorkflow(saved ? "" : saveError);
    });
  });
}

function showLanding(message = "", historyMode = "replace") {
  if (!accountInfo) {
    showLogin(message, historyMode);
    return;
  }
  syncAppRoute({ view: "home" }, historyMode);
  addTopbar();
  const main = document.querySelector("#main");
  const canCreate = licenseIsActive()
    && (accountInfo.unlimited || accountInfo.project_count < accountInfo.project_limit);
  const hasLocalDraft = Boolean(
    localStorage.getItem(STORAGE_KEY)
    || localStorage.getItem(LEGACY_STORAGE_KEY)
    || localStorage.getItem(LEGACY_PAPER_STORAGE_KEY),
  );
  main.className = "shell landing-shell";
  main.innerHTML = `
    <section class="landing" aria-labelledby="page-title">
      <p class="eyebrow">Conta por código · Escrita acadêmica</p>
      <h1 id="page-title">Seus projetos.</h1>
      <p class="lede">${licenseIsActive()
    ? accountInfo.unlimited
      ? "Acesso do proprietário ativo, sem limite de projetos ou análises no aplicativo."
      : `Licença ativa até ${formatDate(accountInfo.expires_at)}. Você usa ${accountInfo.project_count} de ${accountInfo.project_limit} projetos permitidos.`
    : `A licença venceu em ${formatDate(accountInfo.expires_at)}. Seus projetos foram mantidos: você ainda pode ler e exportar; a edição será liberada quando a licença for renovada.`}</p>
      ${message ? `<p class="notice" role="status">${escapeHtml(message)}</p>` : ""}
      ${canCreate ? `<div class="project-create-actions">
        <button class="button button-primary" type="button" data-create-project="case">Novo relatório de case</button>
        <button class="button" type="button" data-create-project="paper">Novo paper jurídico</button>
      </div>` : licenseIsActive() ? '<p class="notice">Você atingiu o limite de projetos desta conta. Peça a quem forneceu o código para aumentar o limite.</p>' : ""}
      ${hasLocalDraft && licenseIsActive() ? '<button class="text-button import-project-button" type="button" id="import-local-project">Importar projeto salvo neste navegador</button>' : ""}
      <section class="account-projects" aria-labelledby="projects-title">
        <h2 id="projects-title">Projetos da conta</h2>
        ${projectRows.length ? `<div class="account-project-list">${projectRows.map((row) => `
          <article class="account-project">
            <div>
              <p class="eyebrow">${row.project_type === "paper" ? "Paper jurídico" : "Relatório de case"}</p>
              <h3>${escapeHtml(row.title || (row.project_type === "paper" ? "Paper sem título" : "Relatório sem título"))}</h3>
              <p class="field-hint">Atualizado em ${formatDate(row.updated_at)}</p>
            </div>
            <div class="project-controls">
              <button class="button button-primary" type="button" data-open-project="${escapeHtml(row.id)}">Abrir</button>
            </div>
          </article>`).join("")}</div>` : '<p class="field-hint">Ainda não há projetos nesta conta.</p>'}
      </section>
      ${reportModels.map((model) => `
        <section class="model-entry" aria-labelledby="model-entry-${escapeHtml(model.id)}">
          <div>
            <p class="eyebrow">${escapeHtml(model.typeLabel)}</p>
            <h2 id="model-entry-${escapeHtml(model.id)}">${escapeHtml(model.title)}</h2>
            <p>Explore o roteiro com os campos preenchidos e consulte a apresentação completa do trabalho.</p>
          </div>
          <div class="model-entry-actions">
            <button class="button button-primary" type="button" data-model-workflow="${escapeHtml(model.id)}">Ver preenchido</button>
            <button class="button" type="button" data-model-document="${escapeHtml(model.id)}">Ler trabalho completo</button>
          </div>
        </section>`).join("")}
      <div class="notice">Os projetos desta conta são armazenados no servidor e ficam disponíveis em seus dispositivos. Você pode exportar o trabalho em PDF pelo próprio navegador. Não compartilhe seu código de acesso.</div>
    </section>`;
  document.querySelectorAll("[data-create-project]").forEach((button) => {
    button.addEventListener("click", () => createRemoteProject(button.dataset.createProject));
  });
  document.querySelectorAll("[data-open-project]").forEach((button) => {
    button.addEventListener("click", () => openRemoteProject(button.dataset.openProject, "push"));
  });
  document.querySelector("#import-local-project")?.addEventListener("click", async () => {
    if (!window.confirm("O conteúdo do projeto salvo neste navegador será enviado e armazenado no servidor, associado a esta conta. Deseja continuar?")) return;
    try {
      const localProject = loadLocalProject();
      if (!localProject) throw new Error("Não foi encontrado um projeto local para importar.");
      const result = await apiRequest("/projects", {
        method: "POST",
        body: JSON.stringify({ project: localProject }),
      });
      await refreshAccount();
      if (await openRemoteProject(result.id)) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(LEGACY_STORAGE_KEY);
        localStorage.removeItem(LEGACY_PAPER_STORAGE_KEY);
      }
    } catch (error) {
      showLanding(error.message);
    }
  });
  document.querySelectorAll("[data-model-workflow]").forEach((button) => {
    button.addEventListener("click", () => {
      const model = reportModels.find((item) => item.id === button.dataset.modelWorkflow);
      if (model) showModelWorkflow(model, false, 0, "push");
    });
  });
  document.querySelectorAll("[data-model-document]").forEach((button) => {
    button.addEventListener("click", () => {
      const model = reportModels.find((item) => item.id === button.dataset.modelDocument);
      if (model) showModelDocument(model, false, null, "push");
    });
  });
}

function renderProgressBar(progress) {
  return `<div class="progress-track" role="progressbar" aria-label="Progresso dos requisitos do trabalho" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress.percent}">
    <span class="progress-fill" style="width:${progress.percent}%"></span>
  </div>`;
}

function renderAssistantControl(fieldRef, value, label = "Revisar este texto") {
  return `<div class="field-assistant">
    <button class="text-button" type="button" data-project-ai-review="${escapeHtml(fieldRef)}" ${!canEditProject() || !String(value ?? "").trim() || !project.fields.assignmentPrompt.trim() || aiAnalysisInProgress || accountInfo?.deepseek_explanation_remaining === 0 ? "disabled" : ""}>${escapeHtml(label)}</button>
    <div class="project-ai-result" data-project-ai-result="${escapeHtml(fieldRef)}">${renderProjectAiReview(value, fieldRef)}</div>
  </div>`;
}

function renderField(field) {
  const id = `field-${field.id}`;
  const value = project.fields[field.id] ?? "";
  const extraHint = field.id === "abstract"
    ? `${String(value).trim().split(/\s+/).filter(Boolean).length} palavras (recomendação: 150–250).`
    : "";
  const help = [field.hint, extraHint].filter(Boolean).join(" ");
  const hint = help ? `<p class="field-hint" id="${id}-hint">${escapeHtml(help)}</p>` : "";
  let control;
  if (field.type === "textarea") {
    control = `<textarea id="${id}" name="${field.id}" data-size="${field.size ?? ""}" ${field.required ? "required" : ""} ${field.hint ? `aria-describedby="${id}-hint"` : ""}></textarea>`;
  } else if (field.type === "select") {
    control = `<select id="${id}" name="${field.id}" ${field.hint ? `aria-describedby="${id}-hint"` : ""}>
      ${field.options.map(([option, label]) => `<option value="${escapeHtml(option)}" ${value === option ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}
    </select>`;
  } else {
    control = `<input id="${id}" name="${field.id}" type="text" value="${escapeHtml(value)}" placeholder="${escapeHtml(field.placeholder ?? "")}" ${field.required ? "required" : ""} ${field.hint ? `aria-describedby="${id}-hint"` : ""}>`;
  }
  const assistant = !AI_REVIEW_EXCLUDED_FIELDS.has(field.id)
    && field.type !== "select"
    ? renderAssistantControl(field.id, project.fields[field.id])
    : "";
  return `<div class="field">
    <div class="field-label-row"><label for="${id}">${escapeHtml(field.label)}${field.required ? " *" : ""}</label>${field.required ? '<span class="field-state is-required">Obrigatório</span>' : ""}</div>
    ${control}
    ${hint}
    ${assistant}
  </div>`;
}

function assistantResultKey(action, item) {
  return `${project.id}:${action}:${item}`;
}

function renderProjectAiReview(value, item) {
  const result = projectAssistantResults.get(assistantResultKey("review", item));
  if (!result) return "";
  return `<section class="assistant-feedback">
    <p><strong>Observação:</strong> ${escapeHtml(result.reply)}</p>
    ${result.evidence ? `<p><strong>Evidência encontrada:</strong> ${escapeHtml(result.evidence)}</p>` : ""}
    ${result.suggestions.length ? `<ul>${result.suggestions.map((suggestion) => `
      <li><strong>${escapeHtml(suggestion.point)}</strong> ${escapeHtml(suggestion.action)}</li>`).join("")}</ul>` : ""}
    ${result.rewrite ? `<details>
      <summary>Ver uma versão sugerida</summary>
      <pre>${escapeHtml(result.rewrite)}</pre>
      <button class="text-button" type="button" data-ai-apply-rewrite="${escapeHtml(item)}">Substituir o campo por esta versão</button>
    </details>` : ""}
  </section>`;
}

function renderChecklistSuggestions(result) {
  const suggestions = result.checklist.filter((item) =>
    item.confidence >= AI_CHECKLIST_SUGGESTION_THRESHOLD && item.evidence.trim());
  const returnedIds = new Set(result.checklist.map((item) => item.id));
  const pending = suggestions.filter((item) =>
    !project.checks[item.id] && project.suggestedChecks[item.id] !== "suggested");
  const manual = result.checklist.filter((item) =>
    item.confidence < AI_CHECKLIST_SUGGESTION_THRESHOLD || !item.evidence.trim());
  for (const [id, label] of Object.entries(result.labels)) {
    if (!returnedIds.has(id)) manual.push({ id, label, evidence: "Sem avaliação clara; confira manualmente." });
  }
  if (result.stale) {
    return `<section class="assistant-feedback">
      <p class="notice">Esta sugestão está desatualizada porque o conteúdo do projeto mudou. Não a aplique sem solicitar uma nova avaliação.</p>
      ${project.suggestedChecks && Object.keys(project.suggestedChecks).length
        ? '<p class="field-hint">As caixas sugeridas anteriormente foram preservadas. Você pode alterá-las ou desfazer as marcações.</p>'
        : ""}
    </section>`;
  }
  return `<section class="assistant-feedback">
    <p>${escapeHtml(result.reply)}</p>
    ${suggestions.length ? `<ul>${suggestions.map((item) => `
      <li><strong>${escapeHtml(result.labels[item.id] ?? item.id)}:</strong> ${escapeHtml(item.evidence)}
        ${project.suggestedChecks[item.id] === "suggested"
          ? '<span class="field-hint">Aceito por você; a caixa continua editável.</span>'
          : project.checks[item.id]
            ? '<span class="field-hint">Já marcado manualmente.</span>'
            : `<button class="text-button" type="button" data-ai-accept-check="${escapeHtml(item.id)}">Aceitar sugestão</button>`}
      </li>`).join("")}</ul>` : '<p>Nenhum item teve evidência suficientemente clara para sugerir marcação.</p>'}
    ${pending.length > 1 ? '<button class="button" type="button" data-ai-accept-all-checks>Aceitar todas as sugestões</button>' : ""}
    ${manual.length ? `<details><summary>Itens para conferência manual (${manual.length})</summary><ul>${manual.map((item) => `
      <li><strong>${escapeHtml(result.labels[item.id] ?? item.label ?? item.id)}:</strong> ${escapeHtml(item.evidence || "Sem evidência clara; confira manualmente.")}</li>`).join("")}</ul></details>` : ""}
    <p class="field-hint">O limiar é apenas um filtro interno, não uma probabilidade de acerto validada. Confira cada caixa.</p>
  </section>`;
}

function renderProjectChat() {
  const messages = projectAssistantConversations.get(project.id) ?? [];
  return `<section class="project-chat" aria-labelledby="project-chat-title">
    <h3 id="project-chat-title">Conversar sobre este trabalho</h3>
    <p class="field-hint">A conversa considera a proposta e os textos acadêmicos do projeto. Não altera os campos. <span id="project-ai-quota">${escapeHtml(deepseekQuotaLabel())}</span> nesta licença.</p>
    ${!project.fields.assignmentPrompt.trim()
      ? '<p class="notice">Preencha a proposta ou as instruções do professor para iniciar a conversa.</p>'
      : ""}
    <div class="project-chat-messages" id="project-chat-messages" aria-live="polite">
      ${messages.length ? messages.map((message) => `
        <article class="project-chat-message" data-role="${message.role}">
          <strong>${message.role === "user" ? "Você" : "Assistente"}</strong>
          <p>${escapeHtml(message.content)}</p>
        </article>`).join("") : '<p class="empty-list">Pergunte sobre clareza, coerência ou pontos a desenvolver no seu trabalho.</p>'}
    </div>
    <div id="project-chat-form" class="project-chat-form">
      <label for="project-chat-input">Sua pergunta</label>
      <textarea id="project-chat-input" maxlength="1200" rows="3" required placeholder="Ex.: Meu problema de pesquisa está alinhado aos objetivos?"></textarea>
      <label class="check-item project-chat-context">
        <input id="project-chat-full-context" type="checkbox" checked>
        <span>Incluir os outros textos do projeto no contexto. A proposta é sempre enviada; referências e dados pessoais não são.</span>
      </label>
      <button class="button" type="button" id="project-chat-send" data-project-ai-chat-send ${!canEditProject() || !project.fields.assignmentPrompt.trim() || aiAnalysisInProgress || accountInfo?.deepseek_explanation_remaining === 0 ? "disabled" : ""}>Enviar pergunta</button>
      <p class="field-hint" id="project-chat-status" role="status" aria-live="polite"></p>
      <p class="field-hint">A conversa fica somente nesta sessão do navegador. O envio usa a cota de assistência.</p>
    </div>
  </section>`;
}

function renderChecks(stage) {
  if (!stage.checks?.length) return "";
  const analysis = stage.analysisSection
    ? caseChecklistAnalyses.get(`${project.id}:${stage.analysisSection}`)
    : null;
  const suggestions = projectAssistantResults.get(`${project.id}:checklist:${project.currentStep}`);
  return `<fieldset class="stage-checklist">
    <legend>Checklist desta etapa</legend>
    ${stage.checks.map(([key, label]) => `
      <label class="check-item">
        <input type="checkbox" data-check="${key}" ${project.checks[key] ? "checked" : ""}>
        <span>${escapeHtml(label)}</span>
      </label>`).join("")}
  </fieldset>
  <section class="ai-analysis-controls" aria-label="Sugestões assistidas da checklist">
    <p class="field-hint">A sugestão só usa evidências encontradas no texto. Itens incertos ficam para conferência manual; nada será marcado sem seu aceite.</p>
    <button class="button" type="button" data-project-ai-checklist ${!canEditProject() || !project.fields.assignmentPrompt.trim() || aiAnalysisInProgress || accountInfo?.deepseek_explanation_remaining === 0 ? "disabled" : ""}>Sugerir preenchimento</button>
    <div class="project-ai-result" data-project-ai-checklist-result aria-live="polite">${suggestions ? renderChecklistSuggestions(suggestions) : ""}</div>
    ${stage.checks.some(([id]) => project.suggestedChecks[id] === "stale")
      ? '<p class="notice">Algumas marcações sugeridas ficaram desatualizadas após uma edição. Confira-as manualmente ou desfaça-as.</p>'
      : ""}
    ${stage.checks.some(([id]) => project.suggestedChecks[id])
      ? '<button class="text-button" type="button" data-ai-undo-checks>Desfazer marcações sugeridas</button>'
      : ""}
  </section>
  ${stage.analysisSection ? `
    <section class="ai-analysis-controls" aria-label="Avaliação automática da checklist">
      <p class="field-hint">Leitura formativa; não é nota oficial nem altera a checklist. <a href="/ajuda-ia/#limits-title" target="_blank" rel="noopener">Como funciona</a>.</p>
      <button class="button" type="button" data-analyze-case-section="${escapeHtml(stage.analysisSection)}" ${aiAnalysisInProgress || !canEditProject() || !project.fields.assignmentPrompt.trim() || accountInfo?.ai_analysis_remaining === 0 ? "disabled" : ""}>Avaliar esta etapa · ${analysisQuotaLabel()}</button>
      <div class="ai-analysis-result" data-ai-analysis-result="section" aria-live="polite">${analysis ? renderChecklistAnalysis(analysis) : ""}</div>
    </section>` : ""}
  ${stage.analysisUnavailable ? `<p class="notice">${escapeHtml(stage.analysisUnavailable)}</p>` : ""}`;
}

function renderCriteria() {
  return `<div class="field-group">
    <div class="field-label-row"><h3>Glossário</h3><button class="button" type="button" id="add-criterion">Adicionar conceito</button></div>
    <p class="field-hint">Para cada conceito, registre a definição e seu fundamento normativo ou ético.</p>
    ${project.criteria.some((item) => item.term === "Conteúdo do rascunho anterior")
      ? '<p class="notice">O texto de critérios do rascunho anterior foi preservado. Reorganize-o em conceitos, definições e fundamentos antes de finalizar o relatório.</p>'
      : ""}
    <div class="criteria-list">
      ${project.criteria.length ? project.criteria.map((item) => `
        <div class="criteria-row" data-criterion="${escapeHtml(item.id)}">
          <div class="field"><label>Conceito</label><input type="text" data-criterion-field="term" value="${escapeHtml(item.term)}">${renderAssistantControl(`criterion:${item.id}:term`, item.term)}</div>
          <div class="field"><label>Definição técnica</label><textarea data-criterion-field="definition">${escapeHtml(item.definition)}</textarea>${renderAssistantControl(`criterion:${item.id}:definition`, item.definition)}</div>
          <div class="field"><label>Base normativa ou ética</label><textarea data-criterion-field="basis">${escapeHtml(item.basis)}</textarea>${renderAssistantControl(`criterion:${item.id}:basis`, item.basis)}</div>
          <button class="text-button remove-button" type="button" data-remove-criterion="${escapeHtml(item.id)}">Remover conceito</button>
        </div>`).join("") : '<p class="empty-list">Nenhum conceito registrado ainda.</p>'}
    </div>
  </div>`;
}

function renderDevelopmentSections() {
  return `<div class="field-group development-sections">
    <div class="field-label-row"><h3>Tópicos do desenvolvimento</h3><button class="button" type="button" id="add-development-section" ${!canEditProject() ? "disabled" : ""}>Adicionar tópico</button></div>
    <p class="field-hint">Adicione quantos tópicos precisar e organize-os na ordem do trabalho.</p>
    ${project.fields.developmentSections.map((section, index) => `
      <article class="development-section" data-development-section="${escapeHtml(section.id)}">
        <div class="field-label-row">
          <h3>Tópico ${index + 1}</h3>
          <div class="development-controls">
            <button class="text-button" type="button" data-development-move="-1" aria-label="Mover tópico ${index + 1} para cima" ${index === 0 ? "disabled" : ""}>↑</button>
            <button class="text-button" type="button" data-development-move="1" aria-label="Mover tópico ${index + 1} para baixo" ${index === project.fields.developmentSections.length - 1 ? "disabled" : ""}>↓</button>
            <button class="text-button remove-button" type="button" data-development-remove ${project.fields.developmentSections.length <= 1 ? "disabled" : ""}>Remover</button>
          </div>
        </div>
        <div class="field">
          <label for="development-title-${escapeHtml(section.id)}">Título do tópico</label>
          <input id="development-title-${escapeHtml(section.id)}" type="text" data-development-field="title" value="${escapeHtml(section.title)}">
          ${renderAssistantControl(`development:${section.id}`, section.title)}
        </div>
        <div class="field">
          <label for="development-content-${escapeHtml(section.id)}">Texto do tópico</label>
          <textarea id="development-content-${escapeHtml(section.id)}" data-size="large" data-development-field="content">${escapeHtml(section.content)}</textarea>
          ${renderAssistantControl(`developmentText:${section.id}`, section.content)}
        </div>
      </article>`).join("")}
  </div>`;
}

function renderSources() {
  const paper = project.projectType === "paper";
  return `<div class="field-group">
    <div class="field-label-row"><h3>Controle de fontes</h3><button class="button" type="button" id="add-source">Adicionar fonte</button></div>
    <p class="field-hint">${paper ? "Registre a referência completa, classifique-a e marque quando ela estiver citada no texto." : "Registre a referência completa, classifique-a, vincule-a à tese em que será usada e marque quando ela estiver citada no texto."} Na lista final, use ordem alfabética única, alinhamento à esquerda, espaçamento simples e uma linha em branco entre entradas. Inclua somente fontes citadas.</p>
    ${project.sources.some((source) => source.category === "pending") ? '<p class="notice">As referências do rascunho anterior foram preservadas. Classifique cada uma e confirme a tese em que foi citada.</p>' : ""}
    <div class="source-list">
      ${project.sources.length ? project.sources.map((source) => `
        <article class="source-row" data-source="${escapeHtml(source.id)}">
          <div class="source-row-head">
            <strong>Fonte</strong>
            <button class="text-button remove-button" type="button" data-remove-source="${escapeHtml(source.id)}">Remover</button>
          </div>
          <div class="field">
            <label>Categoria</label>
            <select data-source-field="category">
              <option value="">Escolha uma categoria</option>
              <option value="pending" ${source.category === "pending" ? "selected" : ""}>Classifique esta fonte importada</option>
              ${sourceTypes.map(([value, label]) => `<option value="${value}" ${source.category === value ? "selected" : ""}>${label}</option>`).join("")}
            </select>
          </div>
          <div class="field">
            <label>Tipo de referência</label>
            <select data-source-field="referenceType">
              ${referenceTypes.map(([value, label]) => `<option value="${value}" ${source.referenceType === value ? "selected" : ""}>${label}</option>`).join("")}
            </select>
          </div>
          ${renderReferenceFields(source)}
          <div class="field">
            <div class="field-label-row"><label for="source-reference-${escapeHtml(source.id)}">Referência formatada</label>
              ${source.referenceType !== "manual" ? `<button class="text-button" type="button" data-format-reference="${escapeHtml(source.id)}">Aplicar estrutura</button>` : ""}
            </div>
            <textarea id="source-reference-${escapeHtml(source.id)}" data-source-field="reference" data-size="large">${escapeHtml(source.reference)}</textarea>
            ${renderReferenceGuidance(source.referenceType)}
            ${renderAssistantControl(`source:${source.id}`, source.reference, "Revisar esta referência")}
          </div>
          ${renderReferencePreview(source)}
          ${paper ? "" : `<fieldset class="source-theses">
            <legend>Relacionada a qual tese?</legend>
            ${Object.entries(thesisLabels).map(([key, label]) => `<label class="check-item"><input type="checkbox" data-source-thesis="${key}" ${source.theses.includes(key) ? "checked" : ""}><span>${label}</span></label>`).join("")}
          </fieldset>`}
          ${source.category === "doctrine" ? `<label class="check-item source-flag"><input type="checkbox" data-source-field="library" ${source.library ? "checked" : ""}><span>Obra consultada na Biblioteca Virtual FACSUR</span></label>` : ""}
          <label class="check-item source-flag"><input type="checkbox" data-source-field="cited" ${source.cited ? "checked" : ""}><span>Esta fonte já foi citada no texto</span></label>
        </article>`).join("") : '<p class="empty-list">Nenhuma fonte registrada ainda.</p>'}
    </div>
    <section class="citation-analysis" id="citation-analysis" aria-labelledby="citation-analysis-title">
      <h3 id="citation-analysis-title">Controle de citações e referências</h3>
      <p class="field-hint">Use esta área para conferir as fontes cadastradas e possíveis inconsistências no texto. Ela não altera nem escreve o conteúdo do trabalho.</p>
      ${renderCitationAnalysis()}
    </section>
    <div id="source-requirements">${renderSourceRequirements()}</div>
  </div>`;
}

function renderReferenceFields(source) {
  const fields = referenceFields[source.referenceType] ?? [];
  const structured = fields.map(([key, label, required]) => `
    <div class="field">
      <div class="field-label-row"><label for="source-${escapeHtml(source.id)}-${key}">${escapeHtml(label)}${required ? " *" : ""}</label></div>
      <input id="source-${escapeHtml(source.id)}-${key}" type="text" data-source-field="details:${key}" value="${escapeHtml(source.details[key] ?? "")}">
    </div>`).join("");
  return `<div class="reference-details">
    ${structured}
    <div class="field">
      <label for="source-${escapeHtml(source.id)}-citation-author">Autor ou órgão para citação no texto</label>
      <input id="source-${escapeHtml(source.id)}-citation-author" type="text" data-source-field="details:citationAuthor" value="${escapeHtml(source.details.citationAuthor ?? "")}" placeholder="Silva ou Supremo Tribunal Federal">
    </div>
    <div class="field">
      <label for="source-${escapeHtml(source.id)}-citation-year">Ano para citação</label>
      <input id="source-${escapeHtml(source.id)}-citation-year" type="text" data-source-field="details:citationYear" value="${escapeHtml(getCitationYear(source))}" placeholder="2024">
    </div>
  </div>`;
}

function formatReference(source) {
  const value = (key) => String(source.details[key] ?? "").trim();
  const sequence = (...parts) => parts.map((part) => String(part ?? "").trim()).filter(Boolean).join(" ");
  const punctuation = (text, mark = ".") => {
    const clean = String(text ?? "").trim();
    if (!clean) return "";
    if (mark === "." && /[.!?]$/.test(clean)) return clean;
    return `${clean.replace(/[.,;:]+$/, "")}${mark}`;
  };
  const online = () => sequence(value("url") && `Disponível em: ${value("url")}.`, value("accessDate") && `Acesso em: ${value("accessDate")}.`);
  switch (source.referenceType) {
    case "book":
      return sequence(
        punctuation(value("authors")),
        punctuation(value("title")),
        punctuation(value("edition")),
        sequence(punctuation(value("city"), ":"), punctuation(value("publisher"), ","), punctuation(value("year"))),
      );
    case "article":
      return sequence(
        punctuation(value("authors")),
        punctuation(value("title")),
        sequence(
          punctuation(value("journal"), ","),
          punctuation(value("city"), ","),
          value("volume") && `v. ${value("volume")},`,
          value("issue") && `n. ${value("issue")},`,
          value("pages") && `p. ${value("pages")},`,
          punctuation(value("monthYear")),
        ),
      );
    case "online":
      return sequence(
        punctuation(value("authors")),
        punctuation(value("title")),
        sequence(punctuation(value("site"), ","), punctuation(value("year"))),
        online(),
      );
    case "legislation":
      return sequence(
        value("jurisdiction") && `${value("jurisdiction").toLocaleUpperCase("pt-BR")}.`,
        punctuation(`${value("title")}${value("date") ? `, de ${value("date")}` : ""}`),
        punctuation(value("ementa")),
        punctuation(value("publication")),
        online(),
      );
    case "case-law":
      return sequence(
        value("jurisdiction") && `${value("jurisdiction").toLocaleUpperCase("pt-BR")}.`,
        punctuation(value("tribunal")),
        punctuation(value("party")),
        sequence(value("processType"), value("processNumber") && `nº ${value("processNumber")}.`),
        value("rapporteur") && punctuation(`Relator: ${value("rapporteur")}`),
        punctuation(value("courtBody")),
        value("judgedAt") && punctuation(`Julgado em: ${value("judgedAt")}`),
        punctuation(value("publication")),
        online(),
      );
    default:
      return source.reference;
  }
}

function missingReferenceFields(source) {
  return (referenceFields[source.referenceType] ?? [])
    .filter(([key, , required]) => required && !String(source.details[key] ?? "").trim())
    .map(([, label]) => label.replace(/\s*\(.*\)$/, ""));
}

function getCitationYear(source) {
  if (source.details.citationYear) return String(source.details.citationYear).trim();
  if (source.details.year) return String(source.details.year).trim();
  const dated = source.details.date || source.details.judgedAt || "";
  return String(dated).match(/\b(?:19|20)\d{2}\b/)?.[0] ?? "";
}

function renderReferencePreview(source) {
  if (source.referenceType === "manual") {
    return '<p class="field-hint">Referência manual preservada. Selecione um tipo estruturado para ver campos e modelo de preenchimento.</p>';
  }
  const preview = formatReference(source);
  const missing = missingReferenceFields(source);
  return `<div class="reference-preview" id="reference-preview-${escapeHtml(source.id)}">
    <p class="field-hint">Prévia montada com os dados informados; confira os elementos e a pontuação antes de aplicar.</p>
    <p class="reference-preview-text">${escapeHtml(preview || "Preencha os campos acima para montar a referência.")}</p>
    ${missing.length ? `<p class="field-hint">Dados ainda não informados: ${escapeHtml(missing.join(", "))}.</p>` : ""}
  </div>`;
}

function renderReferenceGuidance(referenceType) {
  const guidance = {
    manual: "Ajuste a referência manualmente conforme o modelo institucional.",
    book: "Modelo do manual: AUTOR. Título: subtítulo. Edição. Local: Editora, ano.",
    article: "Modelo do manual: AUTOR. Título do artigo. Periódico, local, volume, número, páginas e mês/ano.",
    online: "Modelo do manual: AUTOR/ÓRGÃO. Título. Site, ano. Disponível em: URL. Acesso em: data.",
    legislation: "Modelo do manual: JURISDIÇÃO. Identificação e data da norma. Ementa e publicação oficial. URL e acesso, quando disponíveis.",
    "case-law": "Modelo do manual: ÓRGÃO. Tribunal. Tipo e número do processo. Relator, julgamento, publicação oficial, URL e acesso, quando disponíveis.",
  };
  return `<p class="field-hint reference-guidance">${escapeHtml(guidance[referenceType] || guidance.manual)}</p>`;
}

function normalizeSearchText(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

function projectText() {
  const fields = Object.entries(project.fields)
    .filter(([key, value]) => typeof value === "string"
      && !["assignmentPrompt", "title"].includes(key)
      && !["author", "institution", "course", "discipline", "teacher", "classInfo",
        "deliveryDate", "city", "year", "profile", "paperKind"].includes(key))
    .map(([, value]) => value);
  const sections = (project.fields.developmentSections ?? [])
    .flatMap((section) => [section.title, section.content]);
  return [...fields, ...sections].join("\n");
}

function citationMatch(source, text) {
  const author = normalizeSearchText(source.details.citationAuthor);
  const year = getCitationYear(source);
  if (!author || !year) return null;
  const normalized = normalizeSearchText(text);
  const authorPattern = author
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("\\s+");
  const yearPattern = year.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(
    `(?:^|[^\\p{L}\\p{N}])${authorPattern}(?:\\s+et\\s+al\\.?)?[^\\n]{0,32}?(?:\\(|,\\s*)${yearPattern}[a-z]?(?:\\b|[,;)])`,
    "u",
  );
  const match = pattern.exec(normalized);
  return match ? { index: match.index, excerpt: match[0] } : null;
}

function renderCitationAnalysis() {
  const text = projectText();
  const warnings = new Set();
  const sourcesWithCitationData = project.sources.filter((source) =>
    source.details.citationAuthor && getCitationYear(source));
  for (const source of project.sources) {
    const missing = missingReferenceFields(source);
    if (missing.length) warnings.add(`Referência “${source.details.citationAuthor || source.reference || "sem identificação"}”: confira ${missing.join(", ")}.`);
    if ((source.reference || Object.keys(source.details).length) && (!source.details.citationAuthor || !getCitationYear(source))) {
      warnings.add(`Não consegui conferir autor-data de “${source.reference || "fonte sem referência"}”: informe o autor/órgão e o ano usados na citação.`);
    }
    const match = citationMatch(source, text);
    if (match && !source.cited) warnings.add(`Encontrei uma possível citação de “${source.details.citationAuthor}” (${getCitationYear(source)}), mas a fonte não está marcada como citada.`);
    if (!match && source.details.citationAuthor && getCitationYear(source)) {
      warnings.add(`A referência “${source.details.citationAuthor}” (${getCitationYear(source)}) não parece ter uma citação correspondente nos campos do trabalho; confira se ela foi citada ou se a forma autor-data varia.`);
    }
  }
  const knownKeys = sourcesWithCitationData.map((source) =>
    `${normalizeSearchText(source.details.citationAuthor)} ${normalizeSearchText(getCitationYear(source))}`);
  const parentheticalCitations = [...text.matchAll(/\(([^()\n]{1,100}?,\s*(?:19|20)\d{2}[a-z]?(?:,\s*(?:p\.|local\.?)\s*[\w.-]+)?)\)/gi)];
  for (const match of parentheticalCitations) {
    const candidate = normalizeSearchText(match[1]).replace(/[(),]/g, " ").replace(/\s+/g, " ").trim();
    if (!knownKeys.some((key) => key && candidate.includes(key))) {
      warnings.add(`Possível citação autor-data sem fonte correspondente cadastrada: (${match[1]}).`);
    }
  }
  const narrativeCitations = [...text.matchAll(
    /((?:[A-ZÀ-Þ][\p{L}'’.-]+\s+){0,3}[A-ZÀ-Þ][\p{L}'’.-]+)\s*\(\s*((?:19|20)\d{2}[a-z]?)(?:,\s*(?:p\.|local\.?)\s*[\w.-]+)?\s*\)/gu,
  )];
  for (const match of narrativeCitations) {
    if (!sourcesWithCitationData.some((source) => citationMatch(source, `${match[1]} (${match[2]})`))) {
      warnings.add(`Possível citação narrativa sem referência correspondente cadastrada: ${match[1]} (${match[2]}).`);
    }
  }
  const quotations = [...text.matchAll(/[“"]([^”"\n]{8,})[”"]/g)];
  for (const match of quotations) {
    const tail = text.slice(match.index + match[0].length, match.index + match[0].length + 100);
    const head = text.slice(Math.max(0, match.index - 100), match.index);
    const citedBefore = /(?:\([^)]*(?:p\.|local\.?)\s*[\w.-]+[^)]*\)|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^.!?\n]{0,60}\(\d{4}[^)]*(?:p\.|local\.?)\s*[\w.-]+[^)]*\))\s*[,;:]?\s*$/i.test(head);
    const citedAfter = /^\s*[,;:]?\s*\([^)]*(?:p\.|local\.?)\s*[\w.-]+[^)]*\)/i.test(tail);
    if (!citedBefore && !citedAfter) {
      warnings.add("Encontrei trecho entre aspas sem página ou localizador próximo; confira se é uma citação direta e complete a indicação da fonte.");
      break;
    }
  }
  const activeWarnings = [...warnings].filter((warning) => !ignoredCitationWarnings.has(warning));
  const ignoredWarnings = [...warnings].filter((warning) => ignoredCitationWarnings.has(warning));
  return `<p class="field-hint">Verificação aproximada, feita neste navegador. As ocorrências são pistas para revisão; o sistema pode não reconhecer variações válidas nem distinguir com certeza citação de outros usos do texto.</p>
    ${activeWarnings.length
      ? `<ul class="citation-warning-list">${activeWarnings.map((warning) => `<li>${escapeHtml(warning)} <button class="text-button" type="button" data-ignore-citation-warning="${escapeHtml(warning)}">Ignorar alerta</button></li>`).join("")}</ul>`
      : '<p class="citation-analysis-clear">Nenhum alerta automático neste momento. Ainda confira as citações e as referências manualmente.</p>'}
    ${ignoredWarnings.length
      ? `<details class="citation-ignored-warnings"><summary>Alertas ignorados (${ignoredWarnings.length})</summary><ul>${ignoredWarnings.map((warning) => `<li>${escapeHtml(warning)} <button class="text-button" type="button" data-restore-citation-warning="${escapeHtml(warning)}">Mostrar novamente</button></li>`).join("")}</ul></details>`
      : ""}`;
}

function renderSourceRequirements() {
  const counts = getSourceCounts();
  if (project.projectType === "paper") {
    return `<div class="source-counts">
      <span>Obras marcadas da Biblioteca Virtual FACSUR: ${counts.libraryTotal}</span>
    </div>
    <ul class="requirement-list">
      ${getSourceRules().map((rule) => `<li class="${rule.done ? "is-done" : "is-missing"}"><span aria-hidden="true">${rule.done ? "✓" : "○"}</span>${escapeHtml(rule.label)}</li>`).join("")}
    </ul>`;
  }
  return `<div class="source-counts">
    <span>Obras doutrinárias FACSUR: ${counts.doctrineTotal}/4</span>
    <span>Tese A: ${counts.doctrineA}/2 obras · ${counts.legalA} fonte(s) legal(is) · ${counts.caseA} decisão(ões)</span>
    <span>Tese B: ${counts.doctrineB}/2 obras · ${counts.legalB} fonte(s) legal(is) · ${counts.caseB} decisão(ões)</span>
  </div>
  <ul class="requirement-list">
    ${getSourceRules().map((rule) => `<li class="${rule.done ? "is-done" : "is-missing"}"><span aria-hidden="true">${rule.done ? "✓" : "○"}</span>${escapeHtml(rule.label)}</li>`).join("")}
  </ul>`;
}

function renderReview() {
  const requirements = getRequirements();
  const progress = getProgress();
  return `<div class="review-panel">
    <div class="review-progress">
      <strong>${progress.percent}%</strong>
      <span>${progress.done} de ${progress.total} requisitos atendidos</span>
      ${renderProgressBar(progress)}
    </div>
    <ul class="requirement-list review-requirements">
      ${requirements.map((requirement) => `
        <li class="${requirement.done ? "is-done" : "is-missing"}">
          <span aria-hidden="true">${requirement.done ? "✓" : "○"}</span>
          <span>${escapeHtml(requirement.label)}</span>
          ${!requirement.done ? `<button class="text-button" type="button" data-go-step="${requirement.step}">Revisar</button>` : ""}
        </li>`).join("")}
    </ul>
    <p class="notice">O progresso reflete os itens registrados; não valida argumentos ou fontes. <a href="/ajuda-ia/#limits-title" target="_blank" rel="noopener">Entenda os limites</a>.</p>
    ${project.projectType === "case" ? `
      <section class="ai-analysis-controls" aria-labelledby="case-analysis-title">
        <h3 id="case-analysis-title">Avaliação orientativa do relatório</h3>
        <p class="field-hint">Estimativa de conteúdo, não nota oficial. Dados enviados e limites: <a href="/ajuda-ia/#sent-title" target="_blank" rel="noopener">ajuda sobre IA</a>.</p>
        <button class="button" type="button" data-analyze-case-report ${aiAnalysisInProgress || !canEditProject() || !project.fields.assignmentPrompt.trim() || accountInfo?.ai_analysis_remaining === 0 ? "disabled" : ""}>Avaliar relatório · ${analysisQuotaLabel()}</button>
        <div class="ai-analysis-result" id="ai-analysis-case-report" aria-live="polite">${project?.id && caseReportAnalyses.has(project.id) ? renderCaseAnalysis(caseReportAnalyses.get(project.id), project.id) : ""}</div>
      </section>` : ""}
    ${renderProjectChat()}
    ${project.finalized
      ? `<div class="notice completion-notice">${project.projectType === "paper" ? "Paper" : "Relatório"} marcado como finalizado. Você ainda pode voltar às etapas e editar o conteúdo.</div>`
      : `<button class="button button-primary finalize-button" type="button" id="finalize-project">Marcar ${project.projectType === "paper" ? "paper" : "relatório"} como finalizado</button>`}
    <p class="field-hint">A checklist acompanha sua revisão, mas não bloqueia a prévia ou o PDF. A exportação é opcional e feita neste navegador.</p>
    <div class="export-actions">
      <button class="button" type="button" id="preview-button">Gerar prévia</button>
      <button class="button button-primary" type="button" id="pdf-button" disabled>Baixar PDF</button>
    </div>
    <div class="preview-body" id="preview-body"><p class="preview-empty">A prévia será gerada somente quando você solicitar.</p></div>
    <div class="preview-status" id="preview-status" role="status" aria-live="polite">Confira o conteúdo e a formatação antes de compartilhar.</div>
  </div>`;
}

function renderCaseAnalysis(analysis, projectId = project?.id) {
  const resultSummary = (probabilities, labels, threshold) => {
    const likelyIndex = probabilities.reduce(
      (best, probability, index) => probability > probabilities[best] ? index : best,
      0,
    );
    const likelyProbability = probabilities[likelyIndex];
    if (likelyProbability < threshold) {
      return "<p>Leitura incerta; não há uma única faixa claramente indicada.</p>";
    }
    return `<p><strong>Leitura mais compatível:</strong> ${escapeHtml(labels[likelyIndex])}.</p>`;
  };
  const criteria = analysis.criteria.map((item) => {
    const probabilities = [
      item.probabilities[0],
      item.probabilities[1] + item.probabilities[2],
      item.probabilities[3],
    ];
    const expectedPoints = item.max_points * (probabilities[1] / 2 + probabilities[2]);
    const explanationKey = `${projectId}:${item.id}`;
    const explanation = caseDeepseekExplanations.get(explanationKey);
    const explanationHtml = explanation
      ? renderDeepseekExplanation(explanation)
      : `<button class="button" type="button" data-explain-case-criterion="${escapeHtml(item.id)}" ${aiAnalysisInProgress || !canEditProject() || accountInfo?.deepseek_explanation_remaining === 0 ? "disabled" : ""}>Entender esta observação · ${deepseekQuotaLabel()}</button>`;
    return `<article class="ai-analysis-item">
      <div class="field-label-row"><strong>${escapeHtml(item.title)}</strong></div>
      <p>${expectedPoints.toFixed(2)} / ${item.max_points.toFixed(2)} pontos estimados.</p>
      ${resultSummary(probabilities, caseAnalysisCategories, analysis.probability_threshold)}
      <div class="deepseek-explanation" data-deepseek-explanation="${escapeHtml(item.id)}">${explanationHtml}</div>
    </article>`;
  }).join("");
  return `<section class="ai-analysis-report">
    <h3>Estimativa orientativa de conteúdo</h3>
    <p><strong>${Number(analysis.expected_points).toFixed(2)} / ${Number(analysis.assessable_points).toFixed(2)} pontos</strong></p>
    <h4>Faixa provável</h4>
    ${resultSummary(analysis.grade_range.probabilities, caseGradeRanges, analysis.probability_threshold)}
    <div class="ai-analysis-list">${criteria}</div>
    <p class="field-hint"><a href="/ajuda-ia/#limits-title" target="_blank" rel="noopener">Critérios e limites desta estimativa</a>.</p>
  </section>`;
}

function renderDeepseekExplanation(explanation) {
  const evidence = explanation.evidence.map((item) => `
    <li><strong>${escapeHtml(item.field)}:</strong> ${escapeHtml(item.observation)}</li>`).join("");
  const nextSteps = explanation.next_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("");
  return `<section class="deepseek-explanation-result">
    <h4>Sobre esta observação</h4>
    <p>${escapeHtml(explanation.interpretation)}</p>
    ${evidence ? `<ul>${evidence}</ul>` : ""}
    ${nextSteps ? `<div><strong>Próximos passos</strong><ul>${nextSteps}</ul></div>` : ""}
    <p class="field-hint"><a href="/ajuda-ia/#quota-title" target="_blank" rel="noopener">Sobre limites e uso</a></p>
  </section>`;
}

function renderChecklistAnalysis(analysis) {
  const labels = ["Sem evidência", "Pouca evidência", "Parcialmente atendido", "Evidência clara"];
  const results = analysis.criteria.map((item) => {
    const probabilities = item.probabilities;
    const likelyIndex = probabilities.reduce(
      (best, probability, index) => probability > probabilities[best] ? index : best,
      0,
    );
    const likelyProbability = probabilities[likelyIndex];
    const uncertain = likelyProbability < analysis.probability_threshold;
    return `<article class="ai-analysis-item">
      <strong>${escapeHtml(item.label)}</strong>
      <p>${uncertain ? "A evidência é inconclusiva." : `Leitura possível: ${escapeHtml(labels[likelyIndex])}.`}</p>
    </article>`;
  }).join("");
  const unassessedLabels = {
    "facts-original": "A comparação com o enunciado original não foi feita; inclua o enunciado opcional para avaliar este item.",
    "thesis-a-length": "A extensão aproximada da tese A não pode ser conferida apenas pelo texto corrido.",
    "thesis-b-length": "A extensão aproximada da tese B não pode ser conferida apenas pelo texto corrido.",
  };
  const unassessed = (analysis.unassessed_checks ?? []).map((checkId) => `
    <li>${escapeHtml(unassessedLabels[checkId] ?? "Este item não pôde ser avaliado pelo texto enviado.")}</li>`).join("");
  return `<section class="ai-analysis-report">
    <h3>Observações desta etapa</h3>
    <p>Leitura formativa; confira o texto e decida se cada caixa representa sua avaliação.</p>
    <div class="ai-analysis-list">${results}</div>
    ${unassessed ? `<div><h4>Não avaliados</h4><ul class="ai-analysis-unassessed">${unassessed}</ul></div>` : ""}
  </section>`;
}

function renderCustom(stage) {
  if (stage.custom === "criteria") return renderCriteria();
  if (stage.custom === "sources") return renderSources();
  if (stage.custom === "review") return renderReview();
  if (stage.custom === "development") return renderDevelopmentSections();
  return "";
}

function showWorkflow(message = "", historyMode = "replace") {
  if (project?.id) {
    syncAppRoute({ view: "project", id: project.id, step: project.currentStep }, historyMode);
  }
  compileVersion += 1;
  generatedSource = "";
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }
  const stages = getStages();
  const index = project.currentStep;
  const stage = stages[index];
  const progress = getProgress();
  addTopbar();
  const main = document.querySelector("#main");
  main.className = "shell app-shell";
  main.innerHTML = `
    <div class="app-heading">
      <div>
        <p class="eyebrow">Projeto da conta · ${project.projectType === "paper" ? "Paper jurídico" : "Relatório de case"}</p>
        <h1>${escapeHtml(project.fields.title || (project.projectType === "paper" ? "Paper sem título" : "Relatório sem título"))}</h1>
      </div>
      <div class="app-heading-actions">
        ${project.projectType === "case" ? '<button class="back-link" type="button" id="view-case-model">Ver modelo preenchido</button>' : ""}
        <button class="back-link" type="button" id="export-project-json">Baixar cópia JSON</button>
        ${projectConflict ? '<button class="back-link" type="button" id="reload-project">Reabrir versão do servidor</button>' : ""}
        ${!accountInfo ? '<button class="back-link" type="button" id="login-again">Entrar novamente</button>' : ""}
        <button class="back-link" type="button" id="home-link">← Início</button>
      </div>
    </div>
    <section class="overall-progress" aria-label="Progresso do trabalho">
      <div class="progress-summary"><strong>Progresso</strong><span>${progress.done}/${progress.total} requisitos · ${progress.percent}%</span></div>
      ${renderProgressBar(progress)}
    </section>
    ${message ? `<p class="notice" role="status">${escapeHtml(message)}</p>` : ""}
    <div class="workspace">
      <nav class="step-nav" aria-label="Etapas do relatório">
        ${stages.map((item, step) => `
          <button class="step-link" type="button" data-step="${step}" aria-current="${step === index ? "step" : "false"}">
            <span class="step-index">${String(step + 1).padStart(2, "0")}</span>
            <span>${escapeHtml(item.title)}</span>
            <span class="step-status" aria-label="${stageComplete(step) ? "Etapa completa" : "Etapa incompleta"}">${stageComplete(step) ? "✓" : "·"}</span>
          </button>`).join("")}
      </nav>
      <section class="step-card" aria-labelledby="step-title">
        <p class="step-count">ETAPA ${String(index + 1).padStart(2, "0")} DE ${String(stages.length).padStart(2, "0")}</p>
        <h2 id="step-title">${escapeHtml(stage.title)}</h2>
        <p class="step-intro">${escapeHtml(stage.intro)}</p>
        <form id="step-form" novalidate>
          ${stage.fields?.length ? `<div class="form-grid">${stage.fields.map(renderField).join("")}</div>` : ""}
          ${renderCustom(stage)}
          ${renderChecks(stage)}
          <div class="step-actions">
            <button class="button" type="button" id="previous" ${index === 0 ? "disabled" : ""}>Anterior</button>
            <span class="save-note" id="save-note">${escapeHtml(saveError || "Salvo na conta")}</span>
            <button class="button button-primary" type="button" id="next">${index === stages.length - 1 ? "Voltar à identificação" : "Continuar"}</button>
          </div>
        </form>
      </section>
    </div>
    <p class="privacy-note">${projectConflict
    ? "Conflito de versão: este rascunho está somente para leitura até reabrir a versão atual do servidor."
    : !accountInfo
    ? "Sessão indisponível: este rascunho está somente para leitura. Baixe uma cópia JSON antes de entrar novamente, se quiser preservá-lo."
    : licenseIsActive()
    ? "O projeto é salvo na sua conta no servidor. As prévias e a exportação PDF são geradas neste navegador."
    : "Licença vencida: projeto em modo somente leitura. Você pode consultar e exportar; a edição será liberada quando a licença for renovada."}</p>`;
  for (const field of stage.fields ?? []) {
    const element = document.querySelector(`#field-${CSS.escape(field.id)}`);
    if (element) element.value = project.fields[field.id] ?? "";
  }
  document.querySelector("#login-again")?.addEventListener("click", () => {
    if (!window.confirm("A sessão expirou ou foi revogada. Baixe uma cópia JSON antes de entrar novamente, se quiser preservar este rascunho. Continuar?")) return;
    showLogin("Entre novamente com seu código para acessar a conta.");
  });
  document.querySelector("#home-link").addEventListener("click", async () => {
    try {
      if (projectConflict && !window.confirm("Há alterações locais em conflito que não foram salvas. Você pode baixar uma cópia JSON antes de sair. Deseja voltar à lista mesmo assim?")) return;
      if (!await flushProjectSave()) return;
      await refreshAccount();
      project = null;
      showLanding("", "push");
    } catch (error) {
      showWorkflow(`Não foi possível atualizar os projetos: ${error.message}`);
    }
  });
  document.querySelector("#export-project-json").addEventListener("click", downloadProjectData);
  document.querySelector("#reload-project")?.addEventListener("click", async () => {
    if (!window.confirm("Reabrir a versão mais recente do servidor descartará as alterações locais deste dispositivo. Baixe uma cópia JSON antes, se quiser preservá-las. Continuar?")) return;
    await openRemoteProject(project.id, "replace");
  });
  document.querySelector("#view-case-model")?.addEventListener("click", () => showModelWorkflow(civilCaseModel, true, 0, "push"));
  document.querySelector("#previous").addEventListener("click", () => moveTo(index - 1));
  document.querySelector("#next").addEventListener("click", () => moveTo(index === stages.length - 1 ? 0 : index + 1));
  document.querySelectorAll("[data-step]").forEach((button) => {
    button.addEventListener("click", () => moveTo(Number(button.dataset.step)));
  });
  document.querySelectorAll("[data-go-step]").forEach((button) => {
    button.addEventListener("click", () => moveTo(Number(button.dataset.goStep)));
  });
  document.querySelector("#step-form").addEventListener("input", onFormInput);
  document.querySelector("#step-form").addEventListener("change", onFormInput);
  document.querySelector("#step-form").addEventListener("click", handleStepAction);
  document.querySelector("#project-chat-send")?.addEventListener("click", sendProjectChatMessage);
  document.querySelector("[data-analyze-case-report]")?.addEventListener("click", analyzeCaseReport);
  document.querySelector("#ai-analysis-case-report")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-explain-case-criterion]");
    if (button) explainCaseCriterion(button.dataset.explainCaseCriterion);
  });
  document.querySelector("[data-analyze-case-section]")?.addEventListener("click", (event) => {
    analyzeCaseSection(event.currentTarget.dataset.analyzeCaseSection);
  });
  document.querySelector("#add-criterion")?.addEventListener("click", () => {
    project.criteria.push({ id: newId(), term: "", definition: "", basis: "" });
    invalidateCaseChecklistAnalyses();
    markEdited();
    showWorkflow();
  });
  document.querySelector("#add-development-section")?.addEventListener("click", () => {
    if (!canEditProject()) return;
    project.fields.developmentSections.push({ id: newId(), title: "", content: "" });
    markEdited();
    showWorkflow();
  });
  document.querySelectorAll("[data-remove-criterion]").forEach((button) => {
    button.addEventListener("click", () => {
      project.criteria = project.criteria.filter((item) => item.id !== button.dataset.removeCriterion);
      invalidateCaseChecklistAnalyses();
      markEdited();
      showWorkflow();
    });
  });
  document.querySelector("#add-source")?.addEventListener("click", () => {
    project.sources.push(emptySource());
    markEdited();
    showWorkflow();
  });
  document.querySelectorAll("[data-format-reference]").forEach((button) => {
    button.addEventListener("click", () => {
      const source = project.sources.find((item) => item.id === button.dataset.formatReference);
      if (!source) return;
      source.reference = formatReference(source);
      const field = document.querySelector(`#source-reference-${CSS.escape(source.id)}`);
      if (field) field.value = source.reference;
      markEdited();
    });
  });
  document.querySelectorAll("[data-remove-source]").forEach((button) => {
    button.addEventListener("click", () => {
      project.sources = project.sources.filter((source) => source.id !== button.dataset.removeSource);
      markEdited();
      showWorkflow();
    });
  });
  document.querySelector("#finalize-project")?.addEventListener("click", finalizeProject);
  document.querySelector("#preview-button")?.addEventListener("click", generatePreview);
  document.querySelector("#pdf-button")?.addEventListener("click", downloadPdf);
  if (!canEditProject()) {
    document.querySelectorAll(
      "#step-form input, #step-form textarea, #step-form select, #add-criterion, [data-remove-criterion], #add-source, [data-format-reference], [data-remove-source], [data-analyze-case-report], [data-analyze-case-section], [data-project-ai-review], [data-project-ai-checklist], [data-ai-accept-check], [data-ai-accept-all-checks], [data-ai-apply-rewrite], [data-ai-apply-check], [data-ai-apply-checks], [data-ai-undo-checks], #add-development-section, [data-development-remove], [data-development-move], #project-chat-input, [data-project-ai-chat-send], #finalize-project",
    ).forEach((control) => {
      control.disabled = true;
    });
    const note = document.querySelector("#save-note");
    if (note) note.textContent = projectConflict
      ? "Somente leitura · conflito de versão"
      : !accountInfo
      ? "Somente leitura · sessão indisponível"
      : "Somente leitura · licença vencida";
  }
}

async function analyzeCaseReport() {
  if (aiAnalysisInProgress || project?.projectType !== "case" || !project?.id || !canEditProject()) return;
  const resultElement = document.querySelector("#ai-analysis-case-report");
  const button = document.querySelector("[data-analyze-case-report]");
  if (!resultElement) return;
  if (!button) return;
  if (!window.confirm(
    `Enviar o relatório e a proposta do professor para uma avaliação orientativa? Nome, conta e lista de referências não são enviados. Não é nota oficial nem valida fontes. ${analysisQuotaConfirmation()} Continuar?`,
  )) return;
  aiAnalysisInProgress = true;
  updateAnalysisButtons();
  resultElement.textContent = "Salvando o relatório e solicitando a estimativa…";
  try {
    if (!await flushProjectSave()) throw new Error("Não foi possível confirmar o salvamento mais recente.");
    const projectId = project.id;
    const analysisRevision = analysisVersionForProject(projectId);
    const response = await apiRequest(
      `/projects/${encodeURIComponent(projectId)}/analyze-case-report`,
      { method: "POST", body: "{}" },
    );
    accountInfo.ai_analysis_used = response.usage.used;
    accountInfo.ai_analysis_remaining = response.usage.remaining;
    updateAnalysisButtons();
    if (project?.id !== projectId || analysisVersionForProject(projectId) !== analysisRevision) {
      resultElement.textContent = "O relatório mudou durante a análise; o resultado desatualizado não foi exibido. Solicite uma nova análise.";
      return;
    }
    caseReportAnalyses.set(projectId, response.analysis);
    resultElement.innerHTML = renderCaseAnalysis(response.analysis, projectId);
  } catch (error) {
    try {
      const session = await apiRequest("/session");
      accountInfo = session.account;
    } catch {
      accountInfo = null;
    }
    updateAnalysisButtons();
    resultElement.textContent = error.message;
  } finally {
    aiAnalysisInProgress = false;
    updateAnalysisButtons();
  }
}

async function explainCaseCriterion(criterionId) {
  if (
    aiAnalysisInProgress
    || project?.projectType !== "case"
    || !project?.id
    || !canEditProject()
  ) return;
  const projectId = project.id;
  const analysis = caseReportAnalyses.get(projectId);
  const criterion = analysis?.criteria.find((item) => item.id === criterionId);
  const resultElement = document.querySelector(
    `[data-deepseek-explanation="${CSS.escape(criterionId)}"]`,
  );
  if (!criterion || !resultElement || caseDeepseekExplanations.has(`${projectId}:${criterionId}`)) return;
  if (!window.confirm(
    `Enviar a observação selecionada e trechos curtos relacionados para uma explicação? Não vai o relatório completo ou sua identidade. Não altera seu texto. ${deepseekQuotaConfirmation()} Continuar?`,
  )) return;
  const analysisRevision = analysisVersionForProject(projectId);
  aiAnalysisInProgress = true;
  updateAnalysisButtons();
  resultElement.textContent = "Preparando uma explicação…";
  try {
    const response = await apiRequest(
      `/projects/${encodeURIComponent(projectId)}/explain-case-criterion`,
      {
        method: "POST",
        body: JSON.stringify({
          criterion: criterionId,
          jev_result: {
            score: criterion.score,
            confidence: criterion.confidence,
            probabilities: criterion.probabilities,
          },
        }),
      },
    );
    accountInfo.deepseek_explanation_used = response.usage.used;
    accountInfo.deepseek_explanation_remaining = response.usage.remaining;
    updateAnalysisButtons();
    if (project?.id !== projectId || analysisVersionForProject(projectId) !== analysisRevision) {
      resultElement.textContent = "O relatório mudou durante a explicação; o resultado desatualizado não foi exibido.";
      return;
    }
    caseDeepseekExplanations.set(`${projectId}:${criterionId}`, response.explanation);
    resultElement.innerHTML = renderDeepseekExplanation(response.explanation);
  } catch (error) {
    try {
      const session = await apiRequest("/session");
      accountInfo = session.account;
    } catch {
      accountInfo = null;
    }
    updateAnalysisButtons();
    if (project?.id === projectId && analysisVersionForProject(projectId) === analysisRevision) {
      resultElement.textContent = error.message;
    }
  } finally {
    aiAnalysisInProgress = false;
    updateAnalysisButtons();
  }
}

function analysisVersionForProject(projectId) {
  return caseAnalysisRevision.get(projectId) ?? 0;
}

function invalidateCaseChecklistAnalyses() {
  if (!project?.id) return;
  const projectId = project.id;
  clearCaseAiResults(projectId);
  document.querySelectorAll('[data-ai-analysis-result="section"]').forEach((element) => {
    element.textContent = "O conteúdo analisado mudou. Solicite uma nova análise para conferir a checklist atual.";
  });
}

function clearCaseAiResults(projectId) {
  caseAnalysisRevision.set(projectId, analysisVersionForProject(projectId) + 1);
  caseReportAnalyses.delete(projectId);
  for (const key of caseChecklistAnalyses.keys()) {
    if (key.startsWith(`${projectId}:`)) caseChecklistAnalyses.delete(key);
  }
  for (const key of caseDeepseekExplanations.keys()) {
    if (key.startsWith(`${projectId}:`)) caseDeepseekExplanations.delete(key);
  }
}

function clearProjectAssistantState() {
  if (!project?.id) return;
  projectAiRevision += 1;
  const prefix = `${project.id}:`;
  for (const [key, result] of projectAssistantResults.entries()) {
    if (!key.startsWith(prefix)) continue;
    if (key.includes(":checklist:")) {
      result.stale = true;
    } else {
      projectAssistantResults.delete(key);
    }
  }
  for (const [checkId, state] of Object.entries(project.suggestedChecks)) {
    if (state === "suggested") project.suggestedChecks[checkId] = "stale";
  }
  projectAssistantConversations.delete(project.id);
  document.querySelectorAll("[data-project-ai-result]").forEach((element) => {
    element.textContent = "O conteúdo do trabalho mudou; peça uma nova revisão para atualizar esta observação.";
  });
  const checklistResult = document.querySelector("[data-project-ai-checklist-result]");
  const currentChecklist = projectAssistantResults.get(
    `${project.id}:checklist:${project.currentStep}`,
  );
  if (checklistResult && currentChecklist) {
    checklistResult.innerHTML = renderChecklistSuggestions(currentChecklist);
  }
  const chatMessages = document.querySelector("#project-chat-messages");
  if (chatMessages) {
    chatMessages.innerHTML = '<p class="empty-list">O trabalho mudou. Inicie uma nova conversa para usar o contexto atualizado.</p>';
  }
}

function assistantFieldValue(fieldRef) {
  if (fieldRef.startsWith("development:")) {
    return project.fields.developmentSections.find(
      (section) => section.id === fieldRef.slice("development:".length),
    )?.title ?? "";
  }
  if (fieldRef.startsWith("developmentText:")) {
    return project.fields.developmentSections.find(
      (section) => section.id === fieldRef.slice("developmentText:".length),
    )?.content ?? "";
  }
  if (fieldRef.startsWith("criterion:")) {
    const [, id, property] = fieldRef.split(":");
    return project.criteria.find((item) => item.id === id)?.[property] ?? "";
  }
  if (fieldRef.startsWith("source:")) {
    return project.sources.find((item) => item.id === fieldRef.slice("source:".length))?.reference ?? "";
  }
  return project.fields[fieldRef] ?? "";
}

function setAssistantFieldValue(fieldRef, value) {
  if (fieldRef.startsWith("development:")) {
    const section = project.fields.developmentSections.find(
      (item) => item.id === fieldRef.slice("development:".length),
    );
    if (section) section.title = value;
    return;
  }
  if (fieldRef.startsWith("developmentText:")) {
    const section = project.fields.developmentSections.find(
      (item) => item.id === fieldRef.slice("developmentText:".length),
    );
    if (section) section.content = value;
    return;
  }
  if (fieldRef.startsWith("criterion:")) {
    const [, id, property] = fieldRef.split(":");
    const criterion = project.criteria.find((item) => item.id === id);
    if (criterion && ["term", "definition", "basis"].includes(property)) criterion[property] = value;
    return;
  }
  if (fieldRef.startsWith("source:")) {
    const source = project.sources.find((item) => item.id === fieldRef.slice("source:".length));
    if (source) source.reference = value;
    return;
  }
  project.fields[fieldRef] = value;
}

async function requestProjectAssistant(action, payload, resultElement = null) {
  if (!project?.id || !canEditProject() || aiAnalysisInProgress) return null;
  if (!project.fields.assignmentPrompt.trim()) {
    if (resultElement) resultElement.textContent = "Preencha a proposta ou as instruções do professor antes de pedir ajuda.";
    return null;
  }
  if (!window.confirm(
    `Enviar a proposta do professor e o contexto acadêmico necessário para esta ação? Nome e dados da conta não são enviados. Na conversa, os outros textos só são enviados se você os incluir. A lista completa de referências não é enviada; se você revisar uma referência, somente a selecionada será incluída. ${deepseekQuotaConfirmation()} Continuar?`,
  )) return null;
  const projectId = project.id;
  const contentRevision = projectAiRevision;
  aiAnalysisInProgress = true;
  updateAnalysisButtons();
  if (resultElement) resultElement.textContent = "Lendo o contexto do projeto…";
  try {
    if (!await flushProjectSave()) throw new Error("Não foi possível confirmar o salvamento mais recente.");
    const response = await apiRequest(
      `/projects/${encodeURIComponent(projectId)}/assistant`,
      { method: "POST", body: JSON.stringify({ action, ...payload }) },
    );
    accountInfo.deepseek_explanation_used = response.usage.used;
    accountInfo.deepseek_explanation_remaining = response.usage.remaining;
    if (project?.id !== projectId || projectAiRevision !== contentRevision) {
      if (resultElement) resultElement.textContent = "O trabalho mudou durante a solicitação; o resultado desatualizado não foi aplicado.";
      return null;
    }
    return response.response;
  } catch (error) {
    try {
      const session = await apiRequest("/session");
      accountInfo = session.account;
    } catch {
      accountInfo = null;
    }
    if (resultElement) resultElement.textContent = error.message;
    return null;
  } finally {
    aiAnalysisInProgress = false;
    updateAnalysisButtons();
  }
}

async function reviewProjectField(fieldRef) {
  const value = assistantFieldValue(fieldRef);
  if (!String(value).trim()) return;
  const resultElement = [...document.querySelectorAll("[data-project-ai-result]")].find(
    (element) => element.dataset.projectAiResult === fieldRef,
  );
  if (!resultElement) return;
  const response = await requestProjectAssistant(
    "review",
    { field_id: fieldRef },
    resultElement,
  );
  if (!response) return;
  projectAssistantResults.set(assistantResultKey("review", fieldRef), response);
  resultElement.innerHTML = renderProjectAiReview(value, fieldRef);
}

async function suggestChecklist(stage) {
  const resultElement = document.querySelector("[data-project-ai-checklist-result]");
  if (!stage?.checks?.length || !resultElement) return;
  const response = await requestProjectAssistant(
    "checklist",
    {
      checklist: stage.checks.map(([id, label]) => ({ id, label })),
    },
    resultElement,
  );
  if (!response) return;
  response.labels = Object.fromEntries(stage.checks);
  projectAssistantResults.set(
    assistantResultKey("checklist", project.currentStep),
    response,
  );
  showWorkflow();
}

function acceptChecklistSuggestions(checkIds) {
  const result = projectAssistantResults.get(
    `${project.id}:checklist:${project.currentStep}`,
  );
  if (!canEditProject() || !result || result.stale) return;
  const requestedIds = checkIds ?? result.checklist.map((item) => item.id);
  let changed = false;
  for (const item of result.checklist) {
    if (
      requestedIds.includes(item.id)
      && item.confidence >= AI_CHECKLIST_SUGGESTION_THRESHOLD
      && item.evidence.trim()
      && !project.checks[item.id]
    ) {
      project.checks[item.id] = true;
      project.suggestedChecks[item.id] = "suggested";
      changed = true;
    }
  }
  if (changed) {
    markEdited(false);
    showWorkflow();
  }
}

function undoChecklistSuggestions() {
  const stage = getStages()[project.currentStep];
  if (!stage?.checks) return;
  let changed = false;
  for (const [checkId] of stage.checks) {
    if (project.suggestedChecks[checkId]) {
      project.checks[checkId] = false;
      delete project.suggestedChecks[checkId];
      changed = true;
    }
  }
  if (changed) {
    markEdited(false);
    showWorkflow();
  }
}

function handleStepAction(event) {
  const citationDismiss = event.target.closest("[data-ignore-citation-warning]");
  if (citationDismiss) {
    ignoredCitationWarnings.add(citationDismiss.dataset.ignoreCitationWarning);
    refreshReferenceTools();
    return;
  }
  const citationRestore = event.target.closest("[data-restore-citation-warning]");
  if (citationRestore) {
    ignoredCitationWarnings.delete(citationRestore.dataset.restoreCitationWarning);
    refreshReferenceTools();
    return;
  }
  const reviewButton = event.target.closest("[data-project-ai-review]");
  if (reviewButton) {
    void reviewProjectField(reviewButton.dataset.projectAiReview);
    return;
  }
  if (event.target.closest("[data-project-ai-checklist]")) {
    void suggestChecklist(getStages()[project.currentStep]);
    return;
  }
  const acceptCheckButton = event.target.closest("[data-ai-accept-check]");
  if (acceptCheckButton) {
    acceptChecklistSuggestions([acceptCheckButton.dataset.aiAcceptCheck]);
    return;
  }
  if (event.target.closest("[data-ai-accept-all-checks]")) {
    acceptChecklistSuggestions(null);
    return;
  }
  const rewriteButton = event.target.closest("[data-ai-apply-rewrite]");
  if (rewriteButton) {
    const fieldRef = rewriteButton.dataset.aiApplyRewrite;
    const result = projectAssistantResults.get(assistantResultKey("review", fieldRef));
    if (result?.rewrite && window.confirm("Substituir este campo pela versão sugerida? O conteúdo atual será trocado.")) {
      setAssistantFieldValue(fieldRef, result.rewrite);
      markEdited();
      showWorkflow();
    }
    return;
  }
  if (event.target.closest("[data-ai-undo-checks]")) {
    undoChecklistSuggestions();
    return;
  }
  const section = event.target.closest("[data-development-section]");
  if (section && event.target.closest("[data-development-remove]")) {
    if (project.fields.developmentSections.length <= 1) return;
    project.fields.developmentSections = project.fields.developmentSections.filter(
      (item) => item.id !== section.dataset.developmentSection,
    );
    markEdited();
    showWorkflow();
    return;
  }
  const moveButton = event.target.closest("[data-development-move]");
  if (section && moveButton) {
    const index = project.fields.developmentSections.findIndex(
      (item) => item.id === section.dataset.developmentSection,
    );
    const targetIndex = index + Number(moveButton.dataset.developmentMove);
    if (index < 0 || targetIndex < 0 || targetIndex >= project.fields.developmentSections.length) return;
    [project.fields.developmentSections[index], project.fields.developmentSections[targetIndex]] = [
      project.fields.developmentSections[targetIndex],
      project.fields.developmentSections[index],
    ];
    markEdited();
    showWorkflow();
  }
}

async function sendProjectChatMessage(event) {
  event?.preventDefault();
  const input = document.querySelector("#project-chat-input");
  const status = document.querySelector("#project-chat-status");
  const question = input?.value.trim();
  if (!question || !input?.checkValidity() || !project?.id) return;
  const projectId = project.id;
  const messages = [...(projectAssistantConversations.get(projectId) ?? [])];
  messages.push({ role: "user", content: question });
  const chatContext = messages.slice(-8);
  const includeProjectContext = document.querySelector("#project-chat-full-context")?.checked;
  const contextFields = includeProjectContext
    ? [...Object.keys(project.fields).filter((key) => typeof project.fields[key] === "string"
      && !AI_REVIEW_EXCLUDED_FIELDS.has(key)), "developmentSections", "criteria"]
    : [];
  if (status) status.textContent = "Preparando resposta…";
  const response = await requestProjectAssistant(
    "chat",
    { messages: chatContext, context_fields: contextFields },
    status,
  );
  if (!response) {
    if (status?.textContent === "Preparando resposta…") status.textContent = "";
    return;
  }
  messages.push({ role: "assistant", content: response.reply });
  projectAssistantConversations.set(projectId, messages.slice(-8));
  if (input) input.value = "";
  const chatMessages = document.querySelector("#project-chat-messages");
  if (chatMessages) {
    chatMessages.innerHTML = projectAssistantConversations.get(projectId).map((message) => `
      <article class="project-chat-message" data-role="${message.role}">
        <strong>${message.role === "user" ? "Você" : "Assistente"}</strong>
        <p>${escapeHtml(message.content)}</p>
      </article>`).join("");
  }
  if (status) status.textContent = "";
}

async function analyzeCaseSection(section) {
  if (aiAnalysisInProgress || project?.projectType !== "case" || !project?.id || !canEditProject()) return;
  const stage = getStages().find((item) => item.analysisSection === section);
  const button = document.querySelector(`[data-analyze-case-section="${CSS.escape(section)}"]`);
  const resultElement = document.querySelector('[data-ai-analysis-result="section"]');
  if (!stage || !button || !resultElement) return;
  const includesPrompt = section === "case_description" && Boolean(project.fields.originalCasePrompt.trim());
  const contentDescription = section === "case_description"
    ? `a narrativa dos fatos, a pergunta-problema${includesPrompt ? " e o enunciado original fornecido pelo professor" : ""}`
    : "somente os textos desta etapa e o contexto jurídico necessário";
  const originalPromptNotice = includesPrompt
    ? " O enunciado original também será enviado."
    : "";
  if (!window.confirm(
    `Enviar ${contentDescription} e a proposta do professor para avaliação?${originalPromptNotice} Não altera as caixas nem verifica fontes. ${analysisQuotaConfirmation()} Continuar?`,
  )) return;
  const projectId = project.id;
  const version = analysisVersionForProject(projectId);
  aiAnalysisInProgress = true;
  updateAnalysisButtons();
  resultElement.textContent = "Salvando esta etapa e analisando a checklist…";
  try {
    if (!await flushProjectSave()) throw new Error("Não foi possível confirmar o salvamento mais recente.");
    const response = await apiRequest(
      `/projects/${encodeURIComponent(projectId)}/analyze-case-section`,
      { method: "POST", body: JSON.stringify({ section }) },
    );
    accountInfo.ai_analysis_used = response.usage.used;
    accountInfo.ai_analysis_remaining = response.usage.remaining;
    if (analysisVersionForProject(projectId) === version) {
      caseChecklistAnalyses.set(`${projectId}:${section}`, response.analysis);
      const activeResult = document.querySelector('[data-ai-analysis-result="section"]');
      if (project?.id === projectId && activeResult) {
        activeResult.innerHTML = renderChecklistAnalysis(response.analysis);
      }
    } else if (project?.id === projectId) {
      const activeResult = document.querySelector('[data-ai-analysis-result="section"]');
      if (activeResult) activeResult.textContent = "O conteúdo mudou durante a análise; o resultado não foi exibido como avaliação da versão atual.";
    }
  } catch (error) {
    try {
      const session = await apiRequest("/session");
      accountInfo = session.account;
    } catch {
      accountInfo = null;
    }
    const activeResult = document.querySelector('[data-ai-analysis-result="section"]');
    if (project?.id === projectId && activeResult) activeResult.textContent = error.message;
  } finally {
    aiAnalysisInProgress = false;
    updateAnalysisButtons();
  }
}

function updateAnalysisButtons() {
  const quota = document.querySelector("#project-ai-quota");
  if (quota) quota.textContent = deepseekQuotaLabel();
  document.querySelectorAll("[data-analyze-case-report]").forEach((button) => {
    const remaining = accountInfo?.ai_analysis_remaining;
    button.textContent = `Avaliar relatório · ${analysisQuotaLabel()}`;
    button.disabled = aiAnalysisInProgress || !canEditProject() || !project?.fields.assignmentPrompt.trim() || remaining === 0;
  });
  document.querySelectorAll("[data-analyze-case-section]").forEach((button) => {
    const remaining = accountInfo?.ai_analysis_remaining;
    button.textContent = `Avaliar esta etapa · ${analysisQuotaLabel()}`;
    button.disabled = aiAnalysisInProgress || !canEditProject() || !project?.fields.assignmentPrompt.trim() || remaining === 0;
  });
  document.querySelectorAll("[data-explain-case-criterion]").forEach((button) => {
    const remaining = accountInfo?.deepseek_explanation_remaining;
    button.textContent = `Entender esta observação · ${deepseekQuotaLabel()}`;
    button.disabled = aiAnalysisInProgress || !canEditProject() || remaining === 0;
  });
  document.querySelectorAll("[data-project-ai-review], [data-project-ai-checklist], [data-project-ai-chat-send]").forEach((button) => {
    button.disabled = aiAnalysisInProgress
      || !canEditProject()
      || !project?.fields.assignmentPrompt.trim()
      || accountInfo?.deepseek_explanation_remaining === 0;
  });
}

function refreshProgress() {
  const progress = getProgress();
  const summary = document.querySelector(".overall-progress .progress-summary span");
  if (summary) summary.textContent = `${progress.done}/${progress.total} requisitos · ${progress.percent}%`;
  const bar = document.querySelector(".overall-progress .progress-track");
  if (bar) {
    bar.setAttribute("aria-valuenow", String(progress.percent));
    bar.querySelector(".progress-fill").style.width = `${progress.percent}%`;
  }
  document.querySelectorAll(".step-link").forEach((button) => {
    const index = Number(button.dataset.step);
    const status = button.querySelector(".step-status");
    status.textContent = stageComplete(index) ? "✓" : "·";
    status.setAttribute("aria-label", stageComplete(index) ? "Etapa completa" : "Etapa incompleta");
  });
  const sourceRequirements = document.querySelector("#source-requirements");
  if (sourceRequirements) sourceRequirements.innerHTML = renderSourceRequirements();
  const finalizeButton = document.querySelector("#finalize-project");
  if (finalizeButton) finalizeButton.disabled = !canEditProject();
  const abstractHint = document.querySelector("#field-abstract-hint");
  const abstractField = document.querySelector("#field-abstract");
  if (abstractHint && abstractField) {
    const words = abstractField.value.trim().split(/\s+/).filter(Boolean).length;
    abstractHint.textContent = `A planilha recomenda 150–250 palavras, cobrindo tema, problema, objetivo, metodologia e resultado principal. ${words} palavras no momento.`;
  }
  refreshReferenceTools();
}

function refreshReferenceTools() {
  for (const source of project.sources) {
    const preview = document.querySelector(`#reference-preview-${CSS.escape(source.id)}`);
    if (preview) preview.outerHTML = renderReferencePreview(source);
  }
  const analysis = document.querySelector("#citation-analysis");
  if (analysis) analysis.innerHTML = renderCitationAnalysis();
}

function markEdited(invalidateAssistant = true) {
  if (!canEditProject()) return;
  if (project.finalized) project.finalized = false;
  generatedSource = "";
  if (invalidateAssistant) clearProjectAssistantState();
  saveProject();
  refreshProgress();
  updateAnalysisButtons();
}

function onFormInput(event) {
  if (!canEditProject()) return;
  const target = event.target;
  if (target.dataset.developmentField) {
    const row = target.closest("[data-development-section]");
    const section = project.fields.developmentSections.find((item) => item.id === row?.dataset.developmentSection);
    if (!section) return;
    section[target.dataset.developmentField] = target.value;
    markEdited();
    return;
  }
  if (target.name && Object.hasOwn(project.fields, target.name)) {
    project.fields[target.name] = target.value;
    if (project.projectType === "case" && target.name !== "assignmentPrompt") {
      invalidateCaseChecklistAnalyses();
    }
    markEdited();
    if (target.name === "paperKind") {
      project.currentStep = 0;
      showWorkflow();
      return;
    }
    const heading = document.querySelector(".app-heading h1");
    if (heading) heading.textContent = project.fields.title || (project.projectType === "paper" ? "Paper sem título" : "Relatório sem título");
    return;
  }
  if (target.dataset.check) {
    delete project.suggestedChecks[target.dataset.check];
    project.checks[target.dataset.check] = target.checked;
    markEdited(false);
    const checklistResult = document.querySelector("[data-project-ai-checklist-result]");
    const result = projectAssistantResults.get(
      `${project.id}:checklist:${project.currentStep}`,
    );
    if (checklistResult && result) {
      checklistResult.innerHTML = renderChecklistSuggestions(result);
    }
    return;
  }
  const sourceRow = target.closest("[data-source]");
  if (sourceRow) {
    const source = project.sources.find((item) => item.id === sourceRow.dataset.source);
    if (!source) return;
    if (target.dataset.sourceThesis) {
      const thesis = target.dataset.sourceThesis;
      source.theses = target.checked
        ? [...new Set([...source.theses, thesis])]
        : source.theses.filter((item) => item !== thesis);
    } else if (target.dataset.sourceField === "cited" || target.dataset.sourceField === "library") {
      source[target.dataset.sourceField] = target.checked;
    } else if (target.dataset.sourceField === "referenceType") {
      source.referenceType = target.value;
      const category = categoryForReferenceType(source.referenceType);
      if (category) source.category = category;
      markEdited();
      showWorkflow();
      return;
    } else if (target.dataset.sourceField?.startsWith("details:")) {
      const key = target.dataset.sourceField.slice("details:".length);
      source.details[key] = target.value;
    } else if (target.dataset.sourceField) {
      source[target.dataset.sourceField] = target.value;
      if (target.dataset.sourceField === "category" && source.category !== "doctrine") source.library = false;
    }
    markEdited();
    if (target.dataset.sourceField === "category") showWorkflow();
    return;
  }
  const criterionRow = target.closest("[data-criterion]");
  if (criterionRow && target.dataset.criterionField) {
    const criterion = project.criteria.find((item) => item.id === criterionRow.dataset.criterion);
    if (!criterion) return;
    criterion[target.dataset.criterionField] = target.value;
    invalidateCaseChecklistAnalyses();
    markEdited();
  }
}

function moveTo(index) {
  const stages = getStages();
  if (index < 0 || index >= stages.length) return;
  project.currentStep = index;
  saveProject();
  showWorkflow("", "push");
}

function finalizeProject() {
  if (!canEditProject()) return;
  if (!allRequirementsComplete() && !window.confirm(
    "Ainda há itens da checklist pendentes. Você pode marcar o trabalho como finalizado e gerar a prévia mesmo assim. Continuar?",
  )) {
    return;
  }
  project.finalized = true;
  project.currentStep = getStages().length - 1;
  saveProject();
  showWorkflow(`${project.projectType === "paper" ? "Paper" : "Relatório"} finalizado. A geração de PDF é opcional.`, "push");
}

function escapeTypstString(value) {
  return JSON.stringify(String(value ?? "").trim());
}

function typstParagraphs(value) {
  return String(value ?? "")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => `#par(justify: true)[#text(${escapeTypstString(paragraph.replace(/\s*\n\s*/g, " "))})]`)
    .join("\n\n");
}

function authors() {
  return String(project.fields.author ?? "").split(/\r?\n/).map((name) => name.trim()).filter(Boolean);
}

function coverPage() {
  const fields = project.fields;
  const facsure = fields.profile === "facsure";
  const institution = facsure ? fields.institution.trim() : "";
  const course = facsure ? fields.course.trim() : "";
  const title = fields.title.trim();
  const location = [fields.city, fields.year].filter(Boolean).join(" — ");
  const details = facsure ? [
    fields.discipline && `Disciplina: ${fields.discipline}`,
    fields.teacher && `Professor(a): ${fields.teacher}`,
    fields.classInfo && `Turma: ${fields.classInfo}`,
    fields.deliveryDate && `Data de entrega: ${fields.deliveryDate}`,
  ].filter(Boolean) : [];
  return `#page(numbering: none)[
  #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
  #align(center)[
    #text(weight: "bold", ${escapeTypstString(institution)})
    #linebreak()
    #text(weight: "bold", ${escapeTypstString(course ? `CURSO DE ${course.toLocaleUpperCase("pt-BR")}` : "")})
  ]
  #v(7.03cm)
  #align(center)[
    #text(weight: "bold", ${escapeTypstString(title)})
    #linebreak()
    #text(${escapeTypstString(authors().join(" e "))})
  ]
  #v(0.5cm)
  #align(right)[${details.map((item) => `#text(${escapeTypstString(item)})`).join("#linebreak()\n")}]
  #v(1fr)
  #align(center)[#text(${escapeTypstString(location)})]
]`;
}

function makeDocumentSource() {
  return project.projectType === "paper" ? makePaperDocumentSource() : makeCaseDocumentSource();
}

function makeCaseDocumentSource() {
  const fields = project.fields;
  const alternativeA = `#par(first-line-indent: (amount: 1.25cm, all: true))[a) #text(${escapeTypstString(fields.decisionA)})]`;
  const alternativeB = `#par(first-line-indent: (amount: 1.25cm, all: true))[b) #text(${escapeTypstString(fields.decisionB)})]`;
  const criteria = project.criteria.map((item) =>
    `#par(first-line-indent: 0pt)[#text(weight: "bold", ${escapeTypstString(`${item.term}:`)})#h(0.2em)#text(${escapeTypstString(`${item.definition} Base normativa ou ética: ${item.basis}`)})]`,
  ).join("\n\n");
  const references = project.sources
    .map((source) => source.reference.trim())
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right, "pt-BR", { sensitivity: "base" }))
    .map((reference) => `#par(first-line-indent: 0pt, justify: false)[#text(${escapeTypstString(reference)})]`)
    .join("\n\n#v(1em)\n\n");
  const fieldsBody = [
    `#section-heading("1 DESCRIÇÃO DO CASO")\n${typstParagraphs(fields.facts)}\n\n${typstParagraphs(fields.problem)}`,
    `#section-heading("2 IDENTIFICAÇÃO E ANÁLISE DO CASO", before: 0em, after: 0.75em)`,
    `#section-heading("2.1 Descrição das decisões possíveis", level: 2, before: 0.75em)\n${typstParagraphs(fields.decisionBasis)}\n\n${alternativeA}\n\n${alternativeB}`,
    `#section-heading("2.2 Descrição dos argumentos", level: 2)\n#section-heading("2.2.1 " + ${escapeTypstString(fields.thesisATitle)}, level: 3)\n${typstParagraphs(fields.thesisA)}\n\n#section-heading("2.2.2 " + ${escapeTypstString(fields.thesisBTitle)}, level: 3)\n${typstParagraphs(fields.thesisB)}`,
    `#section-heading("2.3 Descrição dos critérios e valores", level: 2)\n${criteria}`,
    `#pagebreak()\n#align(center)[#text(weight: "bold")[REFERÊNCIAS]]\n#v(0.6em)\n#set par(leading: 0.43em, spacing: 0pt, first-line-indent: 0pt, justify: false)\n${references}`,
  ].join("\n\n#v(0.8em)\n\n");
  const metadata = authors().map((author) =>
    `#text(${escapeTypstString(author)})#footnote[#text(${escapeTypstString(`Discente do curso de ${fields.course || "Direito"} da ${fields.institution || "instituição de ensino"}.`)})]`,
  );
  if (fields.teacher) {
    metadata.push(`#text(${escapeTypstString(fields.teacher)})#footnote[#text(${escapeTypstString("Docente da disciplina.")})]`);
  }
  return `#set page(paper: "a4", margin: (top: 3cm, left: 3cm, bottom: 2cm, right: 2cm), numbering: "1", number-align: top + right, header-ascent: 48%)
#set text(font: "Arial", size: 12pt, lang: "pt", region: "BR", hyphenate: false)
#set par(leading: 1.5em, spacing: 1em, justify: true, first-line-indent: (amount: 1.25cm, all: true), linebreaks: "simple")
#set heading(numbering: none)
#show footnote.entry: set text(size: 10pt)
#show footnote.entry: set footnote.entry(indent: 0pt, gap: 0.5em)
#show footnote.entry: set par(leading: 0.4em, spacing: 0pt, first-line-indent: 0pt, justify: true)
#let section-heading(title, level: 1, before: 1.5em, after: 1.7em) = {
  let content = if level == 1 { text(weight: "bold", upper(title)) } else if level == 2 { text(weight: "bold", title) } else { emph(title) }
  v(before)
  block(width: 100%)[
    #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
    #content
  ]
  v(after)
}

${coverPage()}
#counter(page).update(2)
#set page(numbering: "1", number-align: top + right)
#v(0.2em)
#align(center)[
  #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
  #text(weight: "bold", ${escapeTypstString(fields.title)})#footnote[#text(${escapeTypstString(`Relatório de case apresentado à disciplina ${fields.discipline || ""} da ${fields.institution || ""}.`)})]
]
#v(2.75em)
#align(right)[
  #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
${metadata.join("\\\n")}
]

${fieldsBody}
`;
}

function typstSection(title, content) {
  const body = typstParagraphs(content);
  if (!body) return "";
  return `#section-heading(${escapeTypstString(title)})\n${body}`;
}

function makePaperDocumentSource() {
  const fields = project.fields;
  const projectDocument = fields.paperKind === "project";
  const body = projectDocument
    ? [
      typstSection("1 TEMA E DELIMITAÇÃO", [fields.area, fields.delimitation, fields.researchContext, fields.researchObject].filter(Boolean).join("\n\n")),
      typstSection("2 PROBLEMA DE PESQUISA", [fields.problemContext, fields.problem].filter(Boolean).join("\n\n")),
      typstSection("3 HIPÓTESE", fields.hypothesis),
      typstSection("4 JUSTIFICATIVA", fields.justification),
      typstSection("5 OBJETIVOS", [
        fields.objectiveGeneral && `Objetivo geral: ${fields.objectiveGeneral}`,
        fields.objective1 && `Objetivos específicos:\n${fields.objective1}`,
        fields.objective2,
        fields.objective3,
      ].filter(Boolean).join("\n\n")),
      typstSection("6 REFERENCIAL TEÓRICO", fields.theory),
      typstSection("7 METODOLOGIA", [
        fields.methodAuthor && `Autor de metodologia adotado: ${fields.methodAuthor}.`,
        fields.nature && `Natureza: ${fields.nature}.`,
        fields.approach && `Abordagem: ${fields.approach}.`,
        fields.ends && `Fins: ${fields.ends}.`,
        fields.procedure && `Procedimentos: ${fields.procedure}.`,
        fields.instruments,
      ].filter(Boolean).join("\n\n")),
      makeReferenceSection("REFERÊNCIAS DO PROJETO"),
    ]
    : makePaperFinalBody(fields);
  const metadata = authors().map((author) =>
    `#text(${escapeTypstString(author)})#footnote[#text(${escapeTypstString(`Discente do curso de ${fields.course || "Direito"} da ${fields.institution || "instituição de ensino"}.`)})]`,
  );
  if (fields.teacher) {
    metadata.push(`#text(${escapeTypstString(fields.teacher)})#footnote[#text(${escapeTypstString("Docente da disciplina.")})]`);
  }
  const titleAndAuthors = projectDocument ? "" : `#v(0.2em)
#align(center)[
  #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
  #text(weight: "bold", ${escapeTypstString(fields.title)})
]
#v(1.2em)
#align(right)[
  #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
  ${metadata.join("\\\n")}
]`;
  const abstract = !projectDocument && fields.abstract
    ? `#par(first-line-indent: 0pt, leading: 1em)[#text(weight: "bold", "RESUMO: ")#text(${escapeTypstString(fields.abstract)})]`
    : "";
  const keywords = !projectDocument && fields.keywords
    ? `#par(first-line-indent: 0pt, leading: 1em)[#text(weight: "bold", "Palavras-chave: ")#text(${escapeTypstString(fields.keywords)})]`
    : "";
  return `${typstPreamble()}
${coverPage()}
#counter(page).update(2)
#set page(numbering: "1", number-align: top + right)
${titleAndAuthors}
${abstract}
${keywords}
${!projectDocument && fields.aiNote ? typstSection("DECLARAÇÃO SOBRE USO DE IA", fields.aiNote) : ""}

${body.filter(Boolean).join("\n\n#v(0.8em)\n\n")}
`;
}

function paperReferences() {
  return project.sources
    .map((source) => source.reference.trim())
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right, "pt-BR", { sensitivity: "base" }))
    .map((reference) => `#par(first-line-indent: 0pt, justify: false)[#text(${escapeTypstString(reference)})]`)
    .join("\n\n#v(1em)\n\n");
}

function makeReferenceSection(title) {
  return `#pagebreak()
#align(center)[#text(weight: "bold", ${escapeTypstString(title)})]
#v(0.6em)
#set par(leading: 1em, spacing: 0pt, first-line-indent: 0pt, justify: false)
${paperReferences()}`;
}

function makePaperFinalBody(fields) {
  const development = [];
  for (const section of fields.developmentSections ?? []) {
    const title = String(section.title ?? "").trim();
    const content = section.content;
    if (title || content) {
      const section = typstSection(`${development.length + 2} ${title || `DESENVOLVIMENTO ${development.length + 1}`}`, content);
      if (section) development.push(section);
    }
  }
  return [
    `#section-heading("1 INTRODUÇÃO")\n${typstParagraphs(fields.introduction)}`,
    ...development,
    typstSection(`${development.length + 2} CONCLUSÃO`, fields.conclusion),
    makeReferenceSection("REFERÊNCIAS"),
  ];
}

function missingDocumentData() {
  const fields = project.fields;
  const missing = [];
  if (!fields.title.trim()) missing.push("título");
  if (!authors().length) missing.push("autoria");
  if (project.projectType === "case") {
    if (!fields.facts.trim()) missing.push("narrativa dos fatos");
    if (!fields.problem.trim()) missing.push("pergunta-problema");
  } else if (fields.paperKind === "project") {
    if (!fields.problem.trim()) missing.push("problema de pesquisa");
  } else {
    if (!fields.introduction.trim()) missing.push("introdução");
    if (!(fields.developmentSections ?? []).some((section) => String(section.content ?? "").trim())) {
      missing.push("texto de pelo menos um tópico do desenvolvimento");
    }
    if (!fields.conclusion.trim()) missing.push("conclusão");
  }
  return missing;
}

function typstPreamble() {
  return `#set page(paper: "a4", margin: (top: 3cm, left: 3cm, bottom: 2cm, right: 2cm), numbering: "1", number-align: top + right, header-ascent: 48%)
#set text(font: "Arial", size: 12pt, lang: "pt", region: "BR", hyphenate: false)
#set par(leading: 1.5em, spacing: 1em, justify: true, first-line-indent: (amount: 1.25cm, all: true), linebreaks: "simple")
#set heading(numbering: none)
#show footnote.entry: set text(size: 10pt)
#show footnote.entry: set footnote.entry(indent: 0pt, gap: 0.5em)
#show footnote.entry: set par(leading: 0.4em, spacing: 0pt, first-line-indent: 0pt, justify: true)
#let section-heading(title, level: 1, before: 1.5em, after: 1.7em) = {
  let content = if level == 1 { text(weight: "bold", upper(title)) } else if level == 2 { text(weight: "bold", title) } else { emph(title) }
  v(before)
  block(width: 100%)[
    #set par(first-line-indent: 0pt, leading: 1em, spacing: 0pt)
    #content
  ]
  v(after)
}`;
}

async function getTypst() {
  if (!typstModule) {
    const [{ $typst }, compilerWasm, rendererWasm] = await Promise.all([
      import("@myriaddreamin/typst.ts/contrib/all-in-one-lite"),
      fetch(document.body.dataset.compilerWasm),
      fetch(document.body.dataset.rendererWasm),
    ]);
    if (!compilerWasm.ok || !rendererWasm.ok) {
      throw new Error("Não foi possível carregar os recursos WebAssembly do Typst.");
    }
    const [compilerModule, rendererModule] = await Promise.all([
      compilerWasm.arrayBuffer(),
      rendererWasm.arrayBuffer(),
    ]);
    $typst.setCompilerInitOptions({
      getWrapper: () => import("@myriaddreamin/typst-ts-web-compiler"),
      getModule: () => compilerModule,
    });
    $typst.setRendererInitOptions({
      getWrapper: () => import("@myriaddreamin/typst-ts-renderer"),
      getModule: () => rendererModule,
    });
    typstModule = $typst;
  }
  return typstModule;
}

function setPreviewStatus(message, tone = "") {
  const status = document.querySelector("#preview-status");
  if (!status) return;
  status.dataset.tone = tone;
  status.textContent = message;
}

async function generatePreview() {
  if (!project) return;
  const previewButton = document.querySelector("#preview-button");
  const pdfButton = document.querySelector("#pdf-button");
  const previewBody = document.querySelector("#preview-body");
  const missing = missingDocumentData();
  if (missing.length) {
    generatedSource = "";
    pdfButton.disabled = true;
    setPreviewStatus(`Para gerar um documento coerente, preencha: ${missing.join(", ")}. As pendências de checklist não bloqueiam a exportação.`, "error");
    return;
  }
  const version = ++compileVersion;
  const source = makeDocumentSource();
  generatedSource = "";
  pdfButton.disabled = true;
  previewButton.disabled = true;
  previewButton.textContent = "Preparando…";
  setPreviewStatus("Inicializando o compilador Typst neste navegador…");
  try {
    const typst = await getTypst();
    const vectorData = await typst.vector({ mainContent: source });
    if (!vectorData) throw new Error("O compilador não retornou uma prévia.");
    const svg = await typst.svg({ vectorData });
    if (!svg) throw new Error("O renderizador não retornou páginas.");
    if (version !== compileVersion) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    previewBody.innerHTML = "";
    const image = document.createElement("img");
    image.src = previewUrl;
    image.alt = `Prévia do ${project.projectType === "paper" ? "paper" : "relatório"} ${project.fields.title}`;
    previewBody.append(image);
    generatedSource = source;
    pdfButton.disabled = false;
    setPreviewStatus("Prévia pronta. Confira a paginação antes de baixar o PDF.");
  } catch (error) {
    if (version !== compileVersion) return;
    previewBody.innerHTML = '<p class="preview-empty">Não foi possível gerar a prévia.</p>';
    setPreviewStatus(`Falha na compilação: ${error.message}`, "error");
  } finally {
    if (version === compileVersion) {
      previewButton.disabled = false;
      previewButton.textContent = "Atualizar prévia";
    }
  }
}

async function downloadPdf() {
  const button = document.querySelector("#pdf-button");
  if (!project || !generatedSource) return;
  button.disabled = true;
  setPreviewStatus("Gerando o PDF neste navegador…");
  try {
    const typst = await getTypst();
    const pdf = await typst.pdf({ mainContent: generatedSource });
    if (!pdf) throw new Error("O compilador não retornou um PDF.");
    const url = URL.createObjectURL(new Blob([pdf], { type: "application/pdf" }));
    const anchor = document.createElement("a");
    const fallbackName = project.projectType === "paper" ? "paper-juridico" : "relatorio-case";
    const filename = (project.fields.title || fallbackName)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || fallbackName;
    anchor.href = url;
    anchor.download = `${filename}.pdf`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setPreviewStatus("PDF gerado e baixado.");
  } catch (error) {
    setPreviewStatus(`Falha ao gerar o PDF: ${error.message}`, "error");
  } finally {
    button.disabled = false;
  }
}

function downloadProjectData() {
  if (!project) return;
  const fallbackName = project.projectType === "paper" ? "paper-juridico" : "relatorio-case";
  const filename = (project.fields.title || fallbackName)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || fallbackName;
  const url = URL.createObjectURL(new Blob([JSON.stringify(project, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${filename}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function startApp() {
  try {
    await refreshAccount();
    await restoreAppRoute(routeFromLocation() ?? { view: "home" });
  } catch (error) {
    showLogin(error.status === 401
      ? ""
      : `Não foi possível conectar ao serviço: ${error.message}`);
  }
}

window.addEventListener("popstate", () => {
  void restoreAppRoute(routeFromLocation() ?? { view: "home" });
});

startApp();

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden" && projectSaveTimer) void flushProjectSave();
});
