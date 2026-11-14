# Propostas e Especificações Futuras (docs/propostas/)

Este diretório concentra propostas técnicas, especificações de arquitetura e roadmaps para evolução futura do **Assistente Acadêmico**.

> [!IMPORTANT]
> **Regra de Ciclo de Vida**:
> Este diretório armazena **apenas** propostas pendentes (em ideação, rascunho ou aguardando implementação).
> **Assim que uma proposta for concluída, testada e implantada em produção, seu arquivo Markdown DEVE ser apagado** do repositório, mantendo apenas a referência histórica e o registro do que foi feito no `CHANGELOG.md` e nos commits. Não faz sentido manter arquivos de propostas antigas aqui após estarem prontas no código ativo.

---

## 1. Padrão de Nomenclatura

Os arquivos devem seguir numeração sequencial de 3 dígitos com slug em minúsculas:

```text
docs/propostas/XXX-nome-da-proposta.md
```

Exemplos:
* `001-promocoes-e-cupons.md`
* `002-exportacao-docx-avancada.md`

---

## 2. Estrutura Padrão de cada Proposta

Ao criar uma nova proposta para que qualquer IA ou desenvolvedor compreenda a ideia, use o seguinte esqueleto:

1. **Status**: `[Rascunho | Em Revisão | Aprovado para Implementação]`
2. **Contexto & Motivação**: O que motivou a proposta e qual benefício traz ao produto.
3. **Arquitetura Proposta**:
   - Modelagem de dados (novas tabelas, colunas, chaves estrangeiras).
   - Fluxos de Controllers, rotas e views.
   - Serviços / Jobs em segundo plano.
4. **Pontos de Atenção & Riscos**:
   - Impactos em integrações externas (Mercado Pago, provedores de IA DeepSeek/Gemini/Claude).
   - Reconciliação financeira / webhooks.
   - Concorrência de dados e bloqueios atômicos.
5. **Critérios de Aceite**: O que precisa estar funcionando e testado para considerar a proposta pronta.
6. **Decisões Pendentes de Produto**: Perguntas de negócio que o dono do produto deve responder antes ou durante o desenvolvimento.

---

## 3. Workflow de Aplicação e Remoção

Quando uma IA ou desenvolvedor for implementar uma proposta deste diretório:

1. **Leitura e Alinhamento**: Ler o arquivo `docs/propostas/XXX-*.md` e esclarecer as decisões pendentes com o responsável.
2. **Implementação e Testes**: Desenvolver as alterações, criar migrações, models, views e escrever testes automatizados em `test/` (garantindo 100% de sucesso na suíte).
3. **Documentação de Release**: Adicionar a nova funcionalidade ao `CHANGELOG.md` na seção da nova versão e atualizar o `README.md`.
4. **Remoção da Proposta**:
   - Apagar o arquivo `docs/propostas/XXX-*.md`.
   - Atualizar a tabela de índice abaixo.
5. **Commit & Deploy**: Comitar a remoção do arquivo de proposta juntamente com a entrega do código no Git (`git rm docs/propostas/XXX-*.md`).

---

## 4. Índice de Propostas Pendentes

| Código | Título | Status | Data de Criação |
| :--- | :--- | :--- | :--- |
| `001` | [Promoções, Cupons de Desconto e Créditos Avulsos](001-promocoes-e-cupons.md) | Aguardando Decisão / Fase 2 | 2026-11-14 |
| `002` | [Monitoramento Operacional e Alertas de Falhas Críticas](002-alertas-monitoramento-webhooks.md) | Rascunho / Proposta | 2026-11-14 |
