# Propostas e Especificações Futuras (RFCs / Roadmaps)

Este diretório (`docs/propostas/`) concentra de forma isolada e padronizada todas as especificações técnicas, propostas de melhoria (RFCs) e roadmaps para evolução futura do **Assistente Acadêmico**.

O objetivo é separar claramente a documentação do código vigente (em produção) das ideias e planejamentos de fases posteriores, evitando qualquer ambiguidade durante testes, deploys ou auditorias.

---

## 1. Padrão de Nomenclatura

Os arquivos devem seguir o padrão sequencial numérico com slug em minúsculas:

```text
docs/propostas/XXX-nome-da-proposta.md
```

Exemplos:
* `001-promocoes-e-cupons.md`
* `002-exportacao-docx-avancada.md`

---

## 2. Estrutura Recomendada de uma Proposta

Cada documento deve conter:
1. **Status**: `[Rascunho | Em Revisão | Aprovado | Implementado | Descartado]`
2. **Contexto & Motivação**: Qual problema resolve ou que capacidade adiciona.
3. **Arquitetura & Modelagem**: Alterações de banco de dados, models, controllers e serviços.
4. **Impactos & Pontos de Atenção**: Integrações externas (ex.: Mercado Pago, provedores de IA), concorrência, migrações de dados ou regressões potenciais.
5. **Decisões Pendentes**: Perguntas abertas de negócio/produto antes de iniciar a implementação.

---

## 3. Índice de Propostas Ativas

| Código | Título | Status | Data |
| :--- | :--- | :--- | :--- |
| `001` | [Promoções, Cupons de Desconto e Créditos Avulsos](001-promocoes-e-cupons.md) | Rascunho / Fase 2 | 2026-11-14 |
