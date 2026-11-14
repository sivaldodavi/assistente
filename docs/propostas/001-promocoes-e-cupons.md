# Roadmap Técnico: Cupons, Promoções e Créditos Avulsos (Fase 2)

Este documento registra os requisitos de arquitetura, pontos de atenção e decisões pendentes para a implementação futura do sistema de promoções, cupons de desconto e créditos avulsos no **Assistente Acadêmico**.

---

## 1. Contexto e Motivação

Com o redesenho do fluxo de checkout de pacotes (release `v0.6.0`), a compra é centralizada em seleção única e geração idempotente de Pix. A próxima evolução comercial compreende:
1. Aplicação de cupons promocionais com desconto percentual ou fixo.
2. Campanhas de desconto com limites de utilização (vagas para os primeiros *N* compradores).
3. Venda flexibilizada de créditos adicionais de IA por unidade ou pacotes sem IA embutida.

---

## 2. Arquitetura Proposta

### 2.1. Modelagem de Dados

* **`Promotion`**
  * `code`: string única (ex.: `BEMVINDO20`, `LANCARESTUDOS`, indexada e em caixa alta).
  * `discount_percent`: inteiro (ex.: `20` para 20% de desconto) ou `discount_cents`.
  * `scope`: enum/string (`all`, `projects_only`, `ai_only`).
  * `usage_limit`: inteiro opcional (limite global de resgates / vagas).
  * `redemptions_count`: inteiro (contador atômico com locking).
  * `valid_from` e `valid_until`: timestamps de vigência.
  * `active`: boolean.

* **`PromotionRedemption`**
  * `promotion_id`: FK para `Promotion`.
  * `account_id`: FK para `Account`.
  * `payment_order_id`: FK para o pedido correspondente.
  * `redeemed_at`: timestamp.
  * *Restrição de unicidade*: `[promotion_id, account_id]` se a regra de negócio permitir apenas 1 uso por conta.

* **Ajuste em Pedidos (`PaymentOrder` ou equivalente)**
  * Registrar campos: `original_amount_cents`, `discount_cents`, `promotion_id`.
  * O `amount_cents` final a ser cobrado via Pix deve refletir o valor com desconto.

---

## 3. Impactos Críticos e Pontos de Atenção

### 3.1. Reconciliação do Webhook do Mercado Pago
* Atualmente, `PaymentService#process_verified_payment` valida se o valor pago bate estritamente com `preço_tabela * quantidade`.
* Com cupom, o webhook precisa validar contra o valor **líquido registrado no pedido** (`order.amount_cents`), caso contrário o webhook marcará o pagamento como `mismatch` e não liberará os créditos do usuário.

### 3.2. Concorrência e Reserva de Vagas
* Em promoções do tipo *"Válido para os primeiros 50 clientes"*:
  * O bloqueio deve usar transação atômica (`with_lock`) no modelo `Promotion`.
  * É necessário definir a política de reserva: a vaga é consumida na geração do Pix ou somente na confirmação do pagamento?
    * *Recomendado*: vaga pré-reservada com expiração junto com o Pix (ex.: 30 min); se o Pix expirar sem pagamento, libera-se a vaga.

### 3.3. Painel Administrativo
* Novas rotas e views sob `/admin/promocoes` (seguindo o padrão já estabelecido em `AdminController` e `AdminAuditEvent`).
* Permite aos administradores criar cupons, pausar campanhas e auditar resgates.

---

## 4. Decisões de Produto Pendentes

Antes de iniciar a codificação da Fase 2, o dono do produto deve definir:

1. **Escopo do Cupom**:
   - O desconto se aplica ao valor total do carrinho, apenas a projetos ou apenas a créditos de IA?
2. **Reutilização**:
   - Uma mesma conta pode usar o mesmo cupom em pedidos distintos futuros ou apenas uma única vez na vida?
3. **Venda de Créditos de IA Unitários**:
   - Venda crédito a crédito (ex.: R$ 0,50/crédito) ou manter em blocos mínimos? (Atenção ao valor mínimo por transação Pix permitido pelo Mercado Pago).
4. **Planos sem IA**:
   - Definir se haverá plano estritamente focado em projetos sem cota de créditos de IA embutida.
