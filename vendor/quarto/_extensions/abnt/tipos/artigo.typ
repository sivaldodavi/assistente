// ============================================================
// EXCLUSIVO DO ARTIGO CIENTÍFICO
// Cabeçalho da 1ª página + bloco de resumo.
// Uso no .qmd:  #import "_extensions/abnt/tipos/artigo.typ": *
// ============================================================
#import "../typst-template.typ": *

#let artigo-cabecalho(titulo: "", subtitulo: none, autores: ()) = {
  align(center)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #text(weight: "bold")[#upper(titulo)]#if subtitulo != none [ \ #subtitulo]
  ]
  v(1em)
  align(right)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #for (nome, nota) in autores [#nome#footnote[#nota] \ ]
  ]
  v(1.5em)
}

#let artigo-resumo(palavras: "", corpo) = block[
  #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 1em, justify: true)
  #text(weight: "bold")[RESUMO:] #corpo

  #text(weight: "bold")[Palavras-chave:] #palavras
]
