# Changelog

Este arquivo registra mudanças relevantes por release. Releases usam tags Git anotadas em SemVer; `v0.1.0` identifica a versão-base implantada (`07dfd91`).

## [0.2.0] - 2026-11-13

### Adicionado

- Perfil institucional obrigatório, navegação recolhível e preços promocionais dos pacotes-base.
- Recargas independentes de 20 avaliações JEV ou 20 orientações de escrita por R$ 9,90, sem alteração do plano da conta.
- Criação guiada e organização de texto existente com propostas revisáveis; o projeto só recebe campos selecionados pela pessoa.
- Rubricas formativas por etapa, histórico JEV vinculado à revisão avaliada, notas recentes nos projetos e métricas de progresso filtráveis.
- Migração incremental para persistir avaliações JEV.

### Custos estimados das recargas

Não havia chamadas registradas em `ProviderUsage` na produção quando esta estimativa foi feita; portanto, os valores abaixo são cenários de planejamento, não custos medidos por usuário.

- **Escrita:** para 20 orientações, estimamos 12 mil tokens de entrada e 4 mil de saída por solicitação. Com a tarifa de referência do DeepSeek Flash de US$ 0,30/M tokens de entrada e US$ 1,20/M de saída, o custo estimado é US$ 0,168, ou **R$ 1,01** usando câmbio conservador de R$ 6/US$. A recarga de R$ 9,90 deixa cerca de **89,8% de margem bruta** antes de tarifas de pagamento, impostos e infraestrutura.
- **JEV:** no cenário máximo de 64 mil tokens de entrada por avaliação e US$ 0,042/M tokens, 20 avaliações custariam US$ 0,05376, ou **R$ 0,32** a R$ 6/US$. A recarga de R$ 9,90 deixa cerca de **96,7% de margem bruta** antes de tarifas, impostos e infraestrutura. A saída não foi cobrada no preço consultado.
- O câmbio de R$ 6/US$ é uma premissa de proteção, não uma cotação contratual. O consumo real varia conforme o tamanho do texto e as tarifas vigentes; créditos correspondem a solicitações, não a uma quantidade garantida de tokens.

Referências consultadas em 2026-11-12: [tarifas da API DeepSeek](https://api-docs.deepseek.com/quick_start/pricing), documentação de preços TypeSafe Jev 1.14 e taxa de câmbio USD/BRL de referência. Tarifas e câmbio devem ser verificados novamente antes de futuros reajustes.
