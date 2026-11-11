# Instruções para agentes — Assistente Acadêmico

Este é o projeto novo do Assistente Acadêmico. Ele não compartilha banco, cookies, volume, código executável ou estado de sessão com o projeto legado.

## Antes de alterar

Leia, nesta ordem:

1. `README.md`;
2. `docs/ia/ARQUITETURA.md`;
3. `docs/ia/DECISOES.md`;
4. `docs/ia/INTERFACE.md`;
5. `docs/ia/PARIDADE-FUNCIONAL-ATUAL.md`;
6. `docs/ia/OPERACAO-BACKUP.md` quando a mudança envolver banco, operação ou deploy;
7. `docs/ia/PLANO-PESQUISA-JURIDICA-E-IA.md` quando a mudança envolver biblioteca, catálogo, pesquisa ou IA;
8. a documentação do domínio que será alterado.

Para qualquer alteração de assistência, JEV, pesquisa jurídica ou modelos públicos, leia também `docs/ia/IA-EDITOR-JEV.md` antes de editar templates, JavaScript ou provedores.

## Regras permanentes

- Responda e documente em português.
- Não leia, copie ou altere banco, contas, projetos ou secrets de produção.
- Testes usam banco temporário e provedores falsos.
- Nunca chame DeepSeek, JEV ou Google durante testes; o contato manual externo não é chamado por testes.
- Secrets entram somente por variáveis de ambiente ou arquivos montados como secret.
- Não coloque token, client secret, cookie, telefone ou conteúdo acadêmico em Git ou log.
- Não crie compatibilidade com o banco legado sem decisão explícita.
- Não crie contas `legacy` na aplicação.
- Não implemente pagamentos automáticos.
- Toda alteração deve atualizar a documentação permanente quando mudar uma regra do domínio.
- A descrição dos fatos pertence à etapa Descrição do caso. Não adicionar cronologia ou Linha do Tempo: o recurso foi explicitamente rejeitado pelo titular.
- Preservar os roteiros, campos, dimensões e navegação por etapas do produto de referência; mudança de framework não autoriza redesenho nem corte de funcionalidades.
- A IA deve aparecer dentro da etapa que ela analisa, nunca como um painel genérico separado. As ações especializadas e o JEV ficam em `app/services/ai_workflows.py`, `app/services/ai_support.py` e `app/domain/case_rubric.py`; consulte esses contratos antes de criar outra ação.
- DeepSeek é o provedor primário das ações estruturadas; Gemini é fallback técnico único e JEV/Typesafe é avaliador separado. Nenhuma resposta altera o trabalho sem confirmação explícita no editor.
- Os modelos da vitrine vêm de `app/domain/public-models.json`, extraído do conteúdo anonimizado do legado. Não reduzir novamente os modelos a placeholders nem misturar dados de contas.

## Verificação mínima

```sh
python3 -m pytest -q
python3 -m compileall -q app ops wsgi.py
```

O build Docker e a medição de RAM entram antes de qualquer pré-produção. O domínio atual só muda após aceite explícito e rollback testado.

O backup diário deve ser mantido por uma única rotina versionada em `ops/assistente-db-backup`; não criar cópias paralelas ou alterar retenção, caminho e permissões sem atualizar também `services/assistente-db-backup.*` e `docs/ia/OPERACAO-BACKUP.md`.
