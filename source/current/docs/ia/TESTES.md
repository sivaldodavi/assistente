# Estratégia de testes da aplicação

## Objetivo

Testes protegem o que o usuário e a operação dependem. Não devem verificar nomes internos, quantidade de helpers ou a forma específica como uma view foi montada.

## Camadas

### Domínio puro

Testar normalização, limites, estados permitidos, revisão, fontes, agenda e regras de uso sem Flask, SQLite real ou rede.

### Contratos web

Usar o cliente de teste do Flask com banco temporário. Verificar status, redirecionamento, sessão, CSRF, isolamento entre contas, payload mínimo e mensagens seguras.

### Fluxos

Cada fluxo importante terá um teste de percurso: entrar, criar, editar, salvar, revisar e exportar. O teste não deve depender de uma sequência de testes anterior nem de dados persistidos em disco.

### Provedores falsos

DeepSeek, JEV, Google e Quarto serão adaptadores substituíveis. Os testes simulam sucesso, timeout, resposta inválida, falha depois da entrega e erro de credencial. O contato manual externo não é chamado por testes.

### Navegador

As telas críticas serão verificadas em navegador em um conjunto curto: entrada, editor Case, fontes, autosave/conflito e PDF. O foco e o conteúdo digitado precisam sobreviver a atualizações parciais.

## Teste rápido e completo

O teste rápido deve cobrir importação, healthcheck, página pública, roteiros acadêmicos e ausência de cronologia, autenticação fake, criação/edição e isolamento. Ele roda a cada alteração.

A suíte completa inclui contratos, fluxos acadêmicos, IA fake, PDF, administração, responsividade e casos de erro. Ela roda antes de checkpoint, pré-produção e troca de domínio.

## Regras de qualidade

- Nenhum teste chama serviço externo real.
- Cada falha deve reproduzir um comportamento esperado, não apenas um número de linha.
- Fixtures criam dados mínimos e explícitos.
- Testes de segurança não imprimem tokens ou conteúdo privado.
- Testes visuais comparam estados sem exigir HTML byte a byte.
- Um recurso não é aceito só porque seu caminho feliz funciona; timeout, conflito e revogação precisam ser tratados.
