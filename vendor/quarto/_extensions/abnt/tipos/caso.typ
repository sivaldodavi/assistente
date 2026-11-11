// ============================================================
// EXCLUSIVO DO RELATÓRIO DE CASE (TGPC e afins)
// Cabeçalho da 1ª página do texto: título, autores com notas.
// Uso no .qmd:  #import "_extensions/abnt/tipos/caso.typ": *
// ============================================================
#import "../typst-template.typ": *

#let caso-cabecalho(titulo: "", nota-titulo: none, autores: ()) = {
  align(center)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #text(weight: "bold")[#upper(titulo)]#if nota-titulo != none [#footnote[#nota-titulo]]
  ]
  v(2.73em)
  align(right)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #for (nome, nota) in autores [#nome#footnote[#nota] \ ]
  ]
  v(1.5em)
}
