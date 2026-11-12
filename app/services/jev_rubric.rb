class JevRubric
  GRADE_RANGES = [
    "0 — 0.00 to 0.87 of the 3.50 assessable content points.",
    "1 — 0.88 to 1.75 of the 3.50 assessable content points.",
    "2 — 1.76 to 2.62 of the 3.50 assessable content points.",
    "3 — 2.63 to 3.50 of the 3.50 assessable content points."
  ].freeze

  SCORE_LEVELS = [
    "0 — Insuficiente: o critério está ausente ou há deficiência substancial.",
    "1 — Parcial, mais próximo de insuficiente: há alguma evidência, mas faltam elementos relevantes.",
    "2 — Parcial, mais próximo de adequado: há evidência substancial, com lacunas restantes.",
    "3 — Adequado: o texto fornecido atende substancialmente ao critério."
  ].freeze

  CHECKLIST_LEVELS = [
    "Esta é uma autoavaliação formativa do item selecionado, não a nota oficial do professor.",
    "0 — O texto não contém evidência de que o item foi atendido.",
    "1 — Evidência fraca: o item não foi atendido ou está materialmente incompleto.",
    "2 — Evidência parcial: alguns requisitos foram atendidos, mas há lacunas.",
    "3 — Evidência clara no texto de que o item foi atendido."
  ].freeze

  RUBRIC = {
    "case_description" => {
      "title" => "Descrição do caso e decisões possíveis",
      "max_points" => 0.5,
      "instructions" => "Avalie este critério de 0,5 ponto somente pela rubrica oficial do relatório de Case: delimitação jurídica do tema, clareza dos personagens, contexto e conflito nos fatos, objetividade do problema e identificação de decisões possíveis. Não reduza a pontuação por recomendações opcionais do guia, como terminar com pergunta literal, seguir ordem específica ou criar seção conceitual separada, salvo exigência expressa do professor. Não exija dicotomia fixa entre teses quando o caso for aberto. Não decida qual posição é juridicamente correta."
    },
    "legal_writing_foundation" => {
      "title" => "Redação jurídica e fundamentação",
      "max_points" => 2.5,
      "instructions" => "Avalie este critério de 2,5 pontos pela rubrica oficial do relatório. Desempenho insuficiente inclui ausência de fundamentação jurídica, doutrina ou decisões possíveis. Desempenho parcial inclui fontes superficiais, citações sem relação clara com o caso ou jurisprudência sem explicar sua conexão. Desempenho adequado requer narrativa e problema claros, pelo menos três obras relevantes identificáveis e usadas no texto, dispositivos aplicáveis identificados diretamente e argumentos coerentes com o caso. Conte apenas obras distintas identificáveis no texto fornecido; a lista de referências e o catálogo da biblioteca não são enviados, portanto não afirme que uma obra está no catálogo nem verifique existência, atualidade ou precisão jurídica. Não avalie debate ou escolha final da dissertação. Não desconte por sugestões opcionais do guia, como quatro obras ou duas por alternativa, número sugerido de páginas, terceira pessoa exclusiva, estrutura fixa de tese, integração de todas as fontes em cada parágrafo ou comentário após cada citação, salvo exigência expressa do professor. Se útil, indique-as apenas como sugestões separadas da pontuação. Não infira extensão ou formatação a partir de texto simples."
    },
    "criteria_and_values" => {
      "title" => "Critérios e valores",
      "max_points" => 0.5,
      "instructions" => "Avalie este critério de 0,5 ponto somente pela rubrica oficial: se a solução jurídica possível é coerente e justificada por critérios normativos ou valores jurídicos. Um glossário separado e abrangente é melhoria opcional do guia, não requisito de pontuação, salvo exigência expressa do professor. Não exija definições de vocabulário jurídico comum nem verifique a correção jurídica dos conceitos ou das fontes."
    }
  }.freeze

  CHECKLISTS = {
    "case_description" => {
      "title" => "Descrição do caso",
      "checks" => [
        [ "facts-neutral", "Mantive a descrição sem antecipar solução ou julgamento.", "Avalie somente se a narrativa dos fatos apresenta os acontecimentos de modo neutro, sem defender um resultado jurídico. Não trate a seleção normal de fatos como viés. É uma sugestão formativa, não requisito oficial, salvo exigência expressa do professor." ],
        [ "facts-relevant", "Apresentei quem, o que, contexto e conflito e cortei o que não altera o caso.", "Avalie se a narrativa identifica atores, acontecimentos, contexto e conflito relevantes e mantém foco nos fatos ligados à pergunta jurídica. Não exija fatos que não constem no enunciado. Cortar todo detalhe não essencial é sugestão de redação, não pontuação oficial separada." ],
        [ "problem-question", "A seção termina com uma pergunta jurídica clara, não respondível apenas com sim ou não.", "Avalie se o problema jurídico está formulado com clareza e ligado aos fatos. Ponto de interrogação literal, pergunta aberta ou posição exata ao final são técnicas de apresentação sugeridas, não requisitos de pontuação, salvo exigência expressa do professor." ],
        [ "facts-original", "Reescrevi os fatos com minhas próprias palavras, sem copiar o enunciado.", "Compare com o texto do professor somente quando assignment_prompt contiver a narrativa original do caso. Se houver apenas instruções gerais ou não houver texto-fonte, não infira o original e indique incerteza. Avalie apenas formulações distintivas aparentemente copiadas; ignore nomes, datas, termos jurídicos, linguagem legal, fatos necessários e frases comuns. Sentido semelhante com redação realmente diferente é paráfrase, não cópia. Em caso de linguagem comum, obrigatória ou ambígua, escolha nível incerto/parcial. Nunca acuse plágio nem calcule percentual; avalie somente evidência textual nesses dois textos." ]
      ]
    },
    "case_decisions" => {
      "title" => "Decisões possíveis",
      "checks" => [
        [ "decisions-clear", "As duas decisões possíveis estão formuladas com clareza.", "Avalie se decisões possíveis são identificáveis e formuladas como resultados jurídicos, não como repetição dos fatos. Seção conceitual separada e formato A/B são opcionais, salvo exigência expressa do professor. Não exija duas teses fixas se o relatório identificar um caso aberto." ],
        [ "decisions-balanced", "As alternativas têm peso jurídico comparável.", "Compare se as alternativas são apresentadas como posições plausíveis e com enquadramento razoavelmente comparável, sem decidir qual é juridicamente correta. Em caso aberto, avalie se linhas concorrentes são exploradas sem declarar prematuramente uma vencedora." ],
        [ "decisions-neutral", "A base conceitual e a apresentação não indicam uma preferência.", "Como sugestão formativa, avalie se a apresentação das alternativas é razoavelmente equilibrada e evita antecipar o resultado. Não é requisito oficial separado, salvo exigência expressa do professor." ]
      ]
    },
    "thesis_a" => {
      "title" => "Alternativa A",
      "checks" => [
        [ "thesis-a-integrated", "Relacionei fundamentos jurídicos à alternativa A.", "Avalie se os fundamentos mencionados apoiam a alternativa A e se relacionam ao caso. O requisito de três ou mais obras vale para o relatório inteiro; não exija quantidade fixa nesta alternativa." ],
        [ "thesis-a-comment", "Expliquei com palavras próprias a relevância das citações para o caso.", "Como sugestão formativa, avalie se o estudante explica como legislação, doutrina e decisões citadas se relacionam ao caso. Comentário após cada citação direta não é requisito oficial separado, salvo exigência expressa do professor." ],
        [ "thesis-a-neutral", "Mantive a análise equilibrada e redigida em terceira pessoa.", "Como sugestão formativa, observe o uso da primeira pessoa ou oportunidades de apresentar o argumento de forma justa. Terceira pessoa exclusiva não é requisito oficial separado, salvo exigência expressa do professor. Não penalize a atribuição comum de argumentos às partes nem exija que o relatório escolha a posição vencedora quando isso pertence à dissertação posterior." ]
      ]
    },
    "thesis_b" => {
      "title" => "Alternativa B",
      "checks" => [
        [ "thesis-b-integrated", "Relacionei fundamentos jurídicos à alternativa B.", "Avalie se os fundamentos mencionados apoiam a alternativa B e se relacionam ao caso. O requisito de três ou mais obras vale para o relatório inteiro; não exija quantidade fixa nesta alternativa." ],
        [ "thesis-b-comment", "Expliquei com palavras próprias a relevância das citações para o caso.", "Como sugestão formativa, avalie se o estudante explica como legislação, doutrina e decisões citadas se relacionam ao caso. Comentário após cada citação direta não é requisito oficial separado, salvo exigência expressa do professor." ],
        [ "thesis-b-neutral", "Mantive a análise equilibrada e redigida em terceira pessoa.", "Como sugestão formativa, observe o uso da primeira pessoa ou oportunidades de apresentar o argumento de forma justa. Terceira pessoa exclusiva não é requisito oficial separado, salvo exigência expressa do professor. Não penalize a atribuição comum de argumentos às partes nem exija que o relatório escolha a posição vencedora quando isso pertence à dissertação posterior." ]
      ]
    },
    "criteria_and_values" => {
      "title" => "Critérios e valores",
      "checks" => [
        [ "criteria-defined", "Defini os conceitos técnicos relevantes e indiquei o fundamento de cada definição.", "Como sugestão formativa, avalie se os conceitos listados têm definições claras e fundamento normativo ou ético. Glossário separado com todos os termos é opcional, salvo exigência expressa do professor." ],
        [ "criteria-covered", "Conferi se os termos técnicos usados nas teses estão explicados nesta seção.", "Como sugestão formativa, compare conceitos importantes e específicos do caso presentes nas argumentações com os explicados nesta seção. Glossário abrangente é opcional, salvo exigência expressa do professor. Ignore vocabulário jurídico comum." ]
      ]
    }
  }.freeze

  UNASSESSABLE_CHECKS = {
    "case_description" => [ "facts-original" ],
    "case_decisions" => [],
    "thesis_a" => [],
    "thesis_b" => [],
    "criteria_and_values" => []
  }.freeze

  def questions(section = nil)
    if section
      definition = CHECKLISTS.fetch(section) { raise ArgumentError, "etapa de avaliação inválida" }
      definition.fetch("checks").to_h do |id, _label, instructions|
        [ id, { "type" => "score", "instructions" => instructions, "criteria" => CHECKLIST_LEVELS } ]
      end
    else
      questions = RUBRIC.to_h do |id, definition|
        [ id, { "type" => "score", "instructions" => definition["instructions"], "criteria" => SCORE_LEVELS } ]
      end
      questions["grade_range"] = {
        "type" => "score",
        "instructions" => "Estime a faixa mais provável para os 3,5 pontos de conteúdo do relatório usando somente os três critérios avaliáveis: descrição/decisões possíveis (0,5), redação/fundamentação (2,5) e critérios/valores (0,5). Selecione 0 para 0,00–0,87, 1 para 0,88–1,75, 2 para 1,76–2,62 ou 3 para 2,63–3,50. São faixas técnicas indicativas, não cortes definidos pelo manual; a escala probabilística 0–3 por critério também é uma estimativa interna. Siga apenas a rubrica oficial, sem pontuar melhorias opcionais do guia. Exclua o critério formal/ABNT de 0,5, o debate e a dissertação final. Não redija nem reescreva o trabalho, não invente autoridades e não apresente a estimativa como nota oficial. Use apenas o conteúdo enviado.",
        "criteria" => GRADE_RANGES
      }
      questions
    end
  end

  def normalize(raw, section: nil)
    answers = raw.is_a?(Hash) ? raw["answers"] : nil
    raise ArgumentError, "respostas de avaliação ausentes" unless answers.is_a?(Hash)

    if section
      definition = CHECKLISTS.fetch(section) { raise ArgumentError, "etapa de avaliação inválida" }
      criteria = definition.fetch("checks").map do |id, label, _instructions|
        { "id" => id, "label" => label }.merge(read_score(answers[id]))
      end
      {
        "model" => raw["model"].presence || "jev-latest",
        "section" => section,
        "criteria" => criteria,
        "probability_threshold" => 0.7,
        "unassessed_checks" => UNASSESSABLE_CHECKS.fetch(section),
        "usage" => raw["usage"].is_a?(Hash) ? raw["usage"] : {}
      }
    else
      criteria = RUBRIC.map do |id, definition|
        { "id" => id, "title" => definition["title"], "max_points" => definition["max_points"] }.merge(read_score(answers[id]))
      end
      expected_points = criteria.sum do |item|
        item["max_points"] * ((item["probabilities"][1] + item["probabilities"][2]) / 2 + item["probabilities"][3])
      end
      {
        "model" => raw["model"].presence || "jev-latest",
        "criteria" => criteria,
        "expected_points" => expected_points.round(2),
        "assessable_points" => RUBRIC.values.sum { |item| item["max_points"] },
        "grade_range" => { "title" => "Faixa de pontuação provável do conteúdo" }.merge(read_score(answers["grade_range"])),
        "probability_threshold" => 0.7,
        "unassessed_points" => 0.5,
        "usage" => raw["usage"].is_a?(Hash) ? raw["usage"] : {}
      }
    end
  end

  private

  def read_score(answer)
    score = answer.is_a?(Hash) ? answer["score"] : nil
    unless score.is_a?(Numeric) && !score.is_a?(TrueClass) && !score.is_a?(FalseClass) && score.finite? && score.between?(0, 3)
      raise ArgumentError, "pontuação de avaliação inválida"
    end

    confidence = answer["confidence"]
    confidence = 0.0 unless confidence.is_a?(Numeric) && confidence.finite? && confidence.between?(0, 1)
    probabilities = answer["probabilities"] || [ 0.25, 0.25, 0.25, 0.25 ]
    if probabilities.is_a?(Hash)
      probabilities = (0..3).map { |index| probabilities[index.to_s] || 0 }
    end
    unless probabilities.is_a?(Array) && probabilities.length == 4 &&
        probabilities.all? { |value| value.is_a?(Numeric) && value.finite? && value.between?(0, 1) }
      probabilities = [ 0.25, 0.25, 0.25, 0.25 ]
    end
    total = probabilities.sum
    probabilities = if total <= 0
      [ 0.25, 0.25, 0.25, 0.25 ]
    elsif !(0.97..1.03).cover?(total)
      probabilities.map { |value| value / total }
    else
      probabilities
    end
    {
      "score" => score,
      "confidence" => confidence,
      "probabilities" => probabilities,
      "observation" => answer["observation"].to_s.first(1000)
    }
  end
end
