# Proposta 002: Monitoramento Operacional e Alertas de Falhas Críticas (Telegram/Discord)

Este documento especifica a implementação de um serviço leve de alertas via Webhook para notificar administradores sobre falhas operacionais críticas no **Assistente Acadêmico**.

---

## 1. Contexto & Motivação

Atualmente, o Assistente Acadêmico possui rotinas e integrações assíncronas rodando em produção na VPS:
1. Reconciliação automática de Pix a cada 10 minutos (`assistente-academico-reconcile.timer`).
2. Backups diários com verificação de integridade do SQLite (`assistente-academico-backup.timer`).
3. Roteamento de IA com fallback sucessivo (DeepSeek -> Gemini -> Claude).

Caso ocorra uma divergência contábil no Mercado Pago (`mismatch`), corrupção de backup ou indisponibilidade total dos provedores de IA, essas falhas atualmente ficam registradas apenas nos logs do container ou no `systemd journal`. Esta proposta define um canal de notificação ativo e imediato.

---

## 2. Arquitetura Proposta

### 2.1. Serviço Notificador (`app/services/operational_notifier.rb`)
- Dispara requisições `HTTP POST` com payload formatado em JSON para a URL configurada em `OPERATIONAL_ALERT_WEBHOOK_URL` (suporte a Discord Webhook ou bot do Telegram).
- Totalmente resiliente e não-bloqueante: falhas no envio do alerta são capturadas silenciosamente e gravadas no `Rails.logger`, sem interromper o fluxo do usuário ou a requisição Rails.

### 2.2. Eventos Gatilho
1. **Mercado Pago Webhook**: Pedido marcado como `status: 'mismatch'` (discrepância de valor pago vs configurado).
2. **IA Multi-Provider**: Quando todos os 3 provedores falharem consecutivamente na mesma requisição de usuário.
3. **Rotina de Backup**: Notificação caso `assistente-academico-backup` encerre com código diferente de 0.

---

## 3. Critérios de Aceite
- [ ] Testes unitários do `OperationalNotifier` usando webmock/stubs locais.
- [ ] Não envio de alertas caso `OPERATIONAL_ALERT_WEBHOOK_URL` não esteja definida (silêncio padrão em desenvolvimento/testes).
- [ ] Remoção deste documento de proposta após merge e deploy em produção (`git rm docs/propostas/002-*.md`).
