// ============================================================
// FORMATO ABNT PARA QUARTO (TYPST)
// Baseado na NBR 14724, NBR 6022, NBR 10520, NBR 6023
// e no Manual de Normatização FACSUR (2025)
// ============================================================

#let abnt-recuo = 1.25cm
#let abnt-corpo = 12pt
#let abnt-nota = 10pt
#let abnt-entrelinha-1-5 = 1.04em
#let abnt-simples = 0.46em
#let abnt-fonte-padrao = ("Liberation Sans",)

// ---- Capa e folha de rosto ---------------------------------------
// Layout medido no PDF do TGPC (Relatório de case):
//   - instituição e curso no topo, centralizados
//   - título em caixa alta e negrito no terço central
//   - autores logo abaixo do título, alinhados à direita
//   - bloco de dados (disciplina, professor, turma, data) à direita
//   - local e ano centralizados na base
// folha-rosto: true gera uma segunda página com a natureza do trabalho.
#let abnt-capa(
  instituicao: "",
  curso: "",
  titulo: "",
  subtitulo: "",
  autores: (),
  dados: (),
  natureza: "",
  orientador: "",
  local: "",
  ano: "",
  folha-rosto: false,
) = {
  let auts = if autores.len() == 0 { "" } else { autores.join(", ", last: " e ") }
  let linha-entrelinha = abnt-entrelinha-1-5

  let topo = [
    #align(center)[
      #text(weight: "bold")[#upper(instituicao)] \
      #upper(curso)
    ]
  ]

  let meio = [
    #align(center)[#block(width: 84%)[
      #set align(center)
      #text(weight: "bold")[#upper(titulo)] \
      #if subtitulo != "" [#subtitulo \ ]
    ]]
  ]

  let direita = [
    #align(right)[
      #set par(first-line-indent: (amount: 0pt, all: true), leading: 1.04em, spacing: 0pt, justify: false)
      #auts #linebreak()
      #for d in dados [
        #d.replace("~", " ") #linebreak()
      ]
    ]
  ]

  let base = [
    #align(center)[#local \ #ano]
  ]

  page(numbering: none)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: linha-entrelinha, spacing: 0pt, justify: false)
    #v(3pt)
    #topo
    #v(198.7pt)
    #meio
    #v(12.5pt)
    #direita
    #place(bottom + center, dy: -6pt)[#base]
  ]

  if folha-rosto {
    page(numbering: none)[
      #set par(first-line-indent: (amount: 0pt, all: true), leading: linha-entrelinha, spacing: 0pt, justify: false)
      #topo
      #v(120pt)
      #meio
      #v(1fr)
      #block(width: 8cm)[
        #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 1em, justify: true)
        #set text(size: abnt-nota)
        #natureza
        #if orientador != "" [\ \ Orientador(a): #orientador]
      ]
      #v(1fr)
      #base
    ]
  }
}

// ---- Documento ----------------------------------------------------
#let abnt-doc(
  titulo: none,
  numeracao: "1",
  numeracao-secoes: "1.1",
  pagina-inicial: none,
  quebra-secoes: false,
  entrelinha: 1.04em,
  fonte: abnt-fonte-padrao,
  capa: none,
  sumario: false,
  corpo,
) = {
  let num-pagina = if numeracao == "none" { none } else { numeracao }
  let num-secao = if numeracao-secoes == "none" { none } else { numeracao-secoes }
  let familia = if type(fonte) == str { (fonte, "Liberation Sans") } else { fonte }

  set document(title: titulo) if titulo != none

  // A4; margens: sup. 3 cm, inf. 2 cm, esq. 3 cm, dir. 2 cm
  set page(
    paper: "a4",
    margin: (top: 3cm, left: 3cm, bottom: 2cm, right: 2cm),
    numbering: num-pagina,
    number-align: top + right,
  )

  // Fonte 12 pt, pt-BR, sem hifenização
  set text(font: familia, size: abnt-corpo, lang: "pt", region: "BR", hyphenate: false)

  // Parágrafo: entrelinha 1,5, recuo 1,25 cm na 1ª linha, justificado
  set par(
    leading: entrelinha,
    spacing: 1em,
    justify: true,
    first-line-indent: (amount: abnt-recuo, all: true),
  )

  if pagina-inicial != none {
    counter(page).update(pagina-inicial)
  }

  set heading(numbering: num-secao)

  // Títulos: nível 1 = caixa alta + negrito; nível 2 = negrito; nível 3 = itálico
  show heading: it => {
    let numero = if it.numbering != none {
      counter(heading).display(it.numbering) + h(0.5em)
    } else { none }

    let conteudo = if it.level == 1 {
      text(weight: "bold", size: abnt-corpo)[#numero#upper(it.body)]
    } else if it.level == 2 {
      text(weight: "bold", size: abnt-corpo)[#numero#it.body]
    } else {
      text(weight: "regular", style: "italic", size: abnt-corpo)[#numero#it.body]
    }

    v(1em)
    block(width: 100%)[
      #set par(first-line-indent: (amount: 0pt, all: true))
      #conteudo
    ]
    v(1em)
  }

  // Notas de rodapé: 10 pt, simples, sem recuo
  show footnote.entry: set text(size: abnt-nota)
  show footnote.entry: set footnote.entry(indent: 0pt, gap: 0.5em)
  show footnote.entry: set par(
    leading: abnt-simples,
    spacing: 0pt,
    first-line-indent: (amount: 0pt, all: true),
    justify: true,
  )

  // Citação direta longa (> ...): recuo 4 cm, 10 pt, simples, sem aspas
  show quote.where(block: true): it => {
    v(1em)
    block(inset: (left: 4cm), width: 100%)[
      #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: true)
      #set text(size: abnt-nota)
      #it.body
    ]
    v(1em)
  }

  if capa != none {
    abnt-capa(..capa)
  }
  if sumario {
    abnt-sumario()
  }

  corpo
}

// ---- Sumário -------------------------------------------------------
#let abnt-sumario(titulo: "SUMÁRIO") = page(numbering: none)[
  #align(center)[#text(weight: "bold")[#titulo]]
  #v(2em)
  #set par(first-line-indent: (amount: 0pt, all: true))
  #outline(title: none, indent: auto)
]

// ---- Referências: página nova + título ----------------------------
#let abnt-referencias(titulo: "REFERÊNCIAS") = {
  v(1em)
  align(center)[#text(weight: "bold")[#titulo]]
  v(1.5em)
}

// ---- Tabela (título acima, fonte abaixo, 10 pt) -------------------
#let abnt-tabela(legenda: none, fonte: none, corpo) = block(breakable: false, width: 100%)[
  #set text(size: abnt-nota)
  #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
  #if legenda != none [#legenda #v(0.5em)]
  #corpo
  #if fonte != none [#v(0.5em) Fonte: #fonte]
]

// ---- Figura (título abaixo, fonte depois, 10 pt) ------------------
#let abnt-figura(legenda: none, fonte: none, corpo) = block(breakable: false, width: 100%)[
  #set text(size: abnt-nota)
  #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
  #align(center)[#corpo]
  #v(0.5em)
  #if legenda != none [#legenda]
  #if fonte != none [\ Fonte: #fonte]
]

// ============================================================
// REFERÊNCIAS POR TIPO (NBR 6023 / Manual FACSUR)
// ============================================================

#let _ref(chave, texto) = (chave: chave, texto: texto)

#let _chave(s) = {
  let t = lower(s)
  for p in ("o ", "a ", "os ", "as ", "um ", "uma ") {
    if t.starts-with(p) { t = t.slice(p.len()) }
  }
  t
}

// Autor: sobrenome em caixa alta. Suporta múltiplos autores separados por ";".
#let _autor(a) = {
  let autores = a.split(";")
  autores.map(x => {
    let x = x.trim()
    if x == "et al." or x == "et al" { return x }
    let p = x.split(",")
    if p.len() > 1 {
      upper(p.at(0).trim()) + "," + p.slice(1).join(",")
    } else {
      upper(x)
    }
  }).join("; ")
}

#let _dispo(url, acesso) = {
  let d = if url != none { " Disponível em: " + url + "." } else { "" }
  let a = if acesso != none { " Acesso em: " + acesso + "." } else { "" }
  d + a
}

#let ref-livro(autor, titulo, local, editora, ano,
  subtitulo: none, edicao: none, url: none, acesso: none, extra: none) = {
  let st = if subtitulo != none { ": " + subtitulo } else { "" }
  let ed = if edicao != none { " " + edicao + if edicao.ends-with(".") { "" } else { "." } } else { "" }
  let ex = if extra != none { " " + extra } else { "" }
  _ref(_chave(autor), [#_autor(autor). #text(weight: "bold")[#titulo#st].#ed #local: #editora, #(ano).#ex#_dispo(url, acesso)])
}

#let ref-capitulo(autor, titulo, obra, organizador, local, editora, ano,
  paginas: none, url: none, acesso: none) = {
  let pg = if paginas != none { " p. " + paginas + "." } else { "" }
  _ref(_chave(autor), [#_autor(autor). #titulo. In: #organizador. #text(weight: "bold")[#obra]. #local: #editora, #(ano).#pg#_dispo(url, acesso)])
}

#let ref-artigo(autor, titulo, periodico, local, data,
  volume: none, numero: none, paginas: none, url: none, acesso: none) = {
  let v = if volume != none { ", v. " + volume } else { "" }
  let n = if numero != none { ", n. " + numero } else { "" }
  let pg = if paginas != none { ", p. " + paginas } else { "" }
  _ref(_chave(autor), [#_autor(autor). #titulo. #text(weight: "bold")[#periodico], #local#v#n#pg, #(data).#_dispo(url, acesso)])
}

#let ref-lei(titulo, local, publicacao, data,
  jurisdicao: "BRASIL", ementa: none, url: none, acesso: none, formato: "diario") = {
  let em = if ementa != none { " " + ementa + "." } else { "" }
  let ref = if formato == "diario" {
    [#jurisdicao. #titulo.#em #publicacao, #local, #(data).#_dispo(url, acesso)]
  } else {
    [#jurisdicao. #titulo.#em #local: #publicacao, #(data).#_dispo(url, acesso)]
  }
  _ref(jurisdicao + " " + titulo, ref)
}

#let ref-juris(tribunal, numero, relator, julgado, publicacao,
  tipo: "Recurso Especial", jurisdicao: "BRASIL", orgao: none, url: none, acesso: none) = {
  let og = if orgao != none { " " + orgao + "." } else { "" }
  _ref(jurisdicao + " " + tribunal, [#jurisdicao. #tribunal. #text(weight: "bold")[#tipo nº #numero.] Relator: #relator.#og Julgado em: #julgado. #publicacao.#_dispo(url, acesso)])
}

#let ref-site(titulo, site, ano, url, acesso, autor: none) = {
  let pre = if autor != none { _autor(autor) + ". " } else { "" }
  let chave = if autor != none { _chave(autor) } else { _chave(titulo) }
  _ref(chave, [#pre#titulo. #text(weight: "bold")[#site], #(ano).#_dispo(url, acesso)])
}

#let ref-doc(titulo, local, orgao, ano,
  autor: none, url: none, acesso: none, nota: none) = {
  let pre = if autor != none { _autor(autor) + ". " } else { "" }
  let nt = if nota != none { " " + nota } else { "" }
  let chave = if autor != none { _chave(autor) } else { _chave(titulo) }
  _ref(chave, [#pre#titulo. #local: #orgao, #(ano).#nt#_dispo(url, acesso)])
}

#let ref-texto(chave, texto) = _ref(_chave(chave), texto)

#let abnt-bibliografia(entradas, titulo: "REFERÊNCIAS", ordenar: false) = {
  abnt-referencias(titulo: titulo)
  set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 1em, justify: false)
  let lista = if ordenar { entradas.sorted(key: e => e.chave) } else { entradas }
  for e in lista [
    #block(spacing: 1em)[#e.texto]
  ]
}
