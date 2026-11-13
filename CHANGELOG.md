# Changelog

Este arquivo registra mudanças relevantes por release. Releases usam tags Git anotadas em SemVer; `v0.1.0` identifica a versão-base implantada (`07dfd91`).

## [0.5.0] - 2026-11-13

### Adicionado

- Adiciona Chat com IA contextualizado por projeto ou etapa, acessível pelo editor e pela navegação, sem persistir o histórico da conversa.
- Integra o desenvolvimento de ideias e a organização de texto existente ao fluxo de criação assistida, com propostas editáveis e confirmação antes de criar.
- Apresenta no cabeçalho do editor ações visíveis para abrir o Chat e avaliar a etapa; o debate não oferece avaliação textual.
- Exibe métricas mensais calculadas a partir de revisões reais salvas.

## [0.4.0] - 2026-11-13

### Alterado

- Unifica o shell autenticado entre projetos, biblioteca e pacotes; atualiza ícones, controle da navegação e menu de perfil.
- Simplifica o Início e a orientação por IA, remove avisos e saldos repetidos e mantém informações de privacidade junto às ações.
- Adiciona título opcional aos novos trabalhos, melhora o feedback ao salvar e torna as linhas da lista de projetos acessíveis por teclado.
- Reorganiza o quadro em telas menores e apresenta o apoio acadêmico como uma folha móvel acessível.
- Calcula o valor do Pix conforme a quantidade, transforma Configurações em diálogo modal e melhora alertas, fichamentos, foco e responsividade.

## [0.3.0] - 2026-11-13

### Adicionado

- Roteamento de orientação com IA em DeepSeek → Gemini → Claude, com fallback apenas para falhas recuperáveis; cada pedido concluído consome um crédito.
- Página própria de Métricas, pacotes separados por projetos e créditos de IA e acesso discreto ao suporte.
- Sugestões clicáveis no guia e na criação assistida, além de etapas agrupadas e ações de PDF/Prévia mais simples nos editores.

### Alterado

- Avaliações formativas não consomem créditos; o limite de frequência e o registro de uso continuam ativos para controle de custo.
- O pacote Essencial passa a custar R$ 50,00, com preço de referência de R$ 100,00; recargas antigas de avaliação deixam de ser oferecidas.
- A vitrine apresenta apenas recargas de IA; pedidos legados já iniciados continuam preservados.
- PDFs não são oferecidos para debate ou dissertação. A documentação de configuração inclui Gemini e Claude.

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
