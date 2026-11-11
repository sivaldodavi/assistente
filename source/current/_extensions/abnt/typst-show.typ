#let _abnt-unescape-hash(value) = value.replace("\\#", "#")

#show: doc => abnt-doc(
$if(title)$
  titulo: _abnt-unescape-hash("$title$"),
$endif$
  numeracao: $if(abnt-numeracao)$"$abnt-numeracao$"$else$"1"$endif$,
  numeracao-secoes: $if(abnt-numeracao-secoes)$"$abnt-numeracao-secoes$"$else$"1.1"$endif$,
  pagina-inicial: $if(abnt-pagina-inicial)$$abnt-pagina-inicial$$else$none$endif$,
  quebra-secoes: $if(abnt-sem-quebra-secoes)$false$else$true$endif$,
  entrelinha: $if(abnt-entrelinha)$$abnt-entrelinha$$else$1.04em$endif$,
  sumario: $if(abnt-sumario)$true$else$false$endif$,
$if(abnt-fonte)$
  fonte: _abnt-unescape-hash("$abnt-fonte$"),
$endif$
$if(abnt-capa)$
  capa: (
    instituicao: _abnt-unescape-hash("$abnt-instituicao$"),
    curso: _abnt-unescape-hash("$abnt-curso$"),
    titulo: _abnt-unescape-hash("$title$"),
    subtitulo: _abnt-unescape-hash("$abnt-subtitulo$"),
    autores: ($for(abnt-autores)$_abnt-unescape-hash("$abnt-autores$"),$endfor$),
    dados: ($for(abnt-dados)$_abnt-unescape-hash("$abnt-dados$"),$endfor$),
    natureza: _abnt-unescape-hash("$abnt-natureza$"),
    orientador: _abnt-unescape-hash("$abnt-orientador$"),
    local: _abnt-unescape-hash("$abnt-local$"),
    ano: _abnt-unescape-hash("$abnt-ano$"),
    folha-rosto: $if(abnt-folha-rosto)$true$else$false$endif$,
  ),
$endif$
  doc,
)
