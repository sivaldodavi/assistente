# Contratos de conta da aplicação

## Identidade

Uma conta tem um identificador interno e uma identidade Google verificada. O e-mail é usado para exibição e contato, mas não substitui o `google_sub` para localizar a identidade do provedor.

A aplicação não transforma uma conta em administrativa apenas porque o e-mail parece especial. Privilégio administrativo será uma configuração explícita e será implementado em etapa própria.

## Perfil

O perfil editável contém nome, instituição, curso, disciplina e orientação. Esses campos são contexto de trabalho e podem ser alterados sem alterar a identidade Google.

O perfil não é usado como prova de identidade, não contém secret e não é enviado a provedor externo sem uma ação de produto que documente isso.

## Termos e IA

O aceite dos termos gerais é obrigatório antes de liberar fluxos que dependem de conta. O consentimento de IA é separado: aceitar os termos não autoriza uma chamada de IA.

A aplicação guarda a versão dos termos e o instante do aceite. Retirar consentimento de IA não apaga os termos gerais nem o conteúdo do projeto.

## Projetos

O proprietário pode excluir um projeto pela lista de trabalhos. A operação exige CSRF e confirmação explícita, remove comentários e compartilhamentos relacionados por cascata e atualiza o contador da conta em uma transação. A aplicação não mantém histórico acadêmico nem restaura versões excluídas.

## Sessão

A sessão Flask contém somente o identificador interno da conta, estado OAuth transitório e token CSRF. O ID token Google não fica na sessão nem é enviado ao frontend.

O fluxo OAuth usa state, nonce e PKCE. State, code, nonce e verifier são de uso único e são removidos após o callback. Falhas redirecionam para a página pública sem revelar credenciais ou resposta do provedor.

## Desenvolvimento

`/auth/dev-login` é exclusivamente uma entrada de desenvolvimento controlada por `ALLOW_DEV_AUTH`. O valor padrão é falso. Testes habilitam a opção explicitamente e usam banco temporário.
