# Backup e restauração do Assistente Acadêmico

O banco principal da aplicação fica em `/opt/servidor/data/assistente-academico/assistente_v2.sqlite3`. O diretório de cópias fica em `/opt/servidor/backups/`. O backup não inclui secrets, código, o banco legado, o catálogo jurídico nem qualquer recurso do `zap-go`.

## Tabelas incluídas no backup

O backup abrange todas as tabelas da aplicação, incluindo as adicionadas nas Fases 1-3:

- `accounts`, `projects`, `project_sharing`, `project_collaborators`, `project_comments`
- `project_revisions` (Fase 3 - histórico de revisões por snapshot)
- `deletion_requests` (Fase 3 - solicitações de auto-exclusão de conta)
- `notification_outbox` (Fase 3 - fila de notificações sem WhatsApp)
- `account_grants` (Fase 3 - ledger de créditos por plano)
- `provider_usage` (expandido Fase 3 - uso de provedores de IA)
- `ai_usage_reservations` (expandido Fase 3 - reservas granulares por ação)
- `shared_catalog_sources`, `shared_catalog_notes`, `shared_catalog_selections` (Biblioteca)
- `schedule_items`, `schedule_tasks` (Agenda)
- `case_conferences`, `dissertation_conferences` (Conferências Case)

## Rotina automática

O timer `assistente-db-backup.timer` executa uma vez por dia às 03:15, com atraso aleatório de até 20 minutos. A opção `Persistent=true` faz o systemd executar a rotina depois que o VPS voltar caso o horário tenha sido perdido. A unidade é oneshot: ela executa, valida e termina; não fica mantendo processo aberto.

A rotina versionada está em `ops/assistente-db-backup`. No VPS ela é instalada em `/usr/local/sbin/assistente-db-backup`, acompanhada por `services/assistente-db-backup.service` e `services/assistente-db-backup.timer`.

Cada execução usa o mecanismo de backup do SQLite para copiar um banco em uso sem simplesmente duplicar um arquivo WAL. Depois da cópia, executa `PRAGMA integrity_check`. Em seguida restaura a cópia para um arquivo temporário e valida novamente a integridade e a presença de tabelas. Só depois dessas verificações o arquivo recebe o nome definitivo. Cópias com mais de 14 dias são removidas automaticamente.

## Verificação operacional

```sh
systemctl status assistente-db-backup.timer --no-pager
systemctl list-timers assistente-db-backup.timer --no-pager
systemctl start assistente-db-backup.service
systemctl status assistente-db-backup.service --no-pager -l
journalctl -u assistente-db-backup.service -n 30 --no-pager
find /opt/servidor/backups -maxdepth 1 -type f -name 'assistente-db-*.sqlite3' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
```

A saída esperada da execução manual é o caminho de uma nova cópia e o status `code=exited, status=0/SUCCESS`. Falha de integridade, falha de restauração ou impossibilidade de gravar a cópia deve deixar a unidade com erro e aparecer no journal; não se deve apagar o banco original para “corrigir” um backup que falhou.

## Restauração segura

Nunca restaure diretamente por cima do banco em produção como primeiro teste. Para inspecionar uma cópia, use um diretório temporário, abra o arquivo em modo somente leitura e execute `PRAGMA integrity_check`. Para uma recuperação real, pare somente o serviço do Assistente, preserve o banco atual com outro nome, copie a versão escolhida para o caminho principal, ajuste proprietário/permissões para o UID/GID do serviço e inicie o serviço novamente. Depois valide `/healthz`, login, listagem de trabalhos e leitura de um projeto.

Uma restauração é uma operação destrutiva sobre o estado atual e deve ser autorizada explicitamente antes de ser aplicada. O legado, o catálogo, o `zap-go` e seus volumes não fazem parte dessa operação.

## Regras para agentes

Não criar outro mecanismo de backup em paralelo. Antes de alterar o caminho do banco, o horário, a retenção ou as permissões, atualizar o script, as units e este documento juntos. Nunca colocar banco, cópia, token, segredo ou conteúdo de conta no Git. O backup é proteção operacional; não é histórico de versões do produto e não deve ser apresentado à pessoa usuária como recurso de restauração de trabalhos.

Ao adicionar novas tabelas via migração (ex: `project_revisions`, `account_grants`, `deletion_requests`), garantir que o script de backup continue copiando o banco completo sem exclusões.
