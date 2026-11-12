// ============================================================
// EXCLUSIVO DO PROJETO DE PESQUISA
// Página de identificação (2ª página) + cabeçalho do texto.
// Uso no .qmd:  #import "_extensions/abnt/tipos/projeto.typ": *
// ============================================================
#import "../typst-template.typ": *

#let pagina-identificacao-projeto(
  curso: "",
  titulo: "PROJETO DE PAPER",
  periodo: "",
  disciplina: "",
  professor: "",
  aluno: "",
) = {
  set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-entrelinha-1-5, spacing: 0.5em, justify: false)
  v(2cm)
  align(center)[
    #text(weight: "bold")[#upper(curso)]
    #v(3cm)
    #text(weight: "bold", size: 14pt)[#upper(titulo)]
    #v(1.5em)
    #if periodo != "" [#text(weight: "bold")[#upper(periodo)] #v(1em)]
    #if disciplina != "" [
      #text(weight: "bold")[DISCIPLINA: ]#upper(disciplina) #linebreak()
    ]
    #if professor != "" [
      #text(weight: "bold")[PROF(A): ]#upper(professor) #linebreak()
    ]
    #if aluno != "" [
      #text(weight: "bold")[ALUNO(A): ]#upper(aluno) #linebreak()
    ]
  ]
}

#let projeto-cabecalho(titulo: "", autores: ()) = {
  align(center)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #text(weight: "bold")[#upper(titulo)]
  ]
  v(1em)
  align(right)[
    #set par(first-line-indent: (amount: 0pt, all: true), leading: abnt-simples, spacing: 0pt, justify: false)
    #for (nome, nota) in autores [#nome#footnote[#nota] \ ]
  ]
  v(1.5em)
}
