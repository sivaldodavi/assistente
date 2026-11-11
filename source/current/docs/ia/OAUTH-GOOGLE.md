# Login Google e configuração externa

O login Google usa três configurações distintas no ambiente operacional:

```text
ASSISTENTE_GOOGLE_CLIENT_ID
ASSISTENTE_GOOGLE_CLIENT_SECRET
ASSISTENTE_GOOGLE_REDIRECT_URI
```

No VPS, os valores ficam em `/opt/servidor/.env`, fora do Git. O Compose injeta essas variáveis somente no container `site-assistente-academico`. O redirect de produção é:

```text
https://trab.sivaldodavi.com.br/oauth/google/callback
```

Esse endereço precisa estar cadastrado no mesmo cliente OAuth do Google. O fluxo usa `state`, `nonce` e PKCE; o callback valida a credencial com `google-auth` antes de criar ou atualizar a conta.

## Secrets que não são Google

Os arquivos abaixo têm outros usos e não podem ser usados como client secret Google:

```text
/opt/servidor/secrets/assistente-academico/deepseek_api_key
/opt/servidor/secrets/assistente-academico/typesafe_api_key
/opt/servidor/secrets/zap/token
```

O segredo da sessão da aplicação é montado separadamente. Nenhum desses arquivos deve ser copiado para o repositório ou exibido em logs.

## Diagnóstico seguro

O início do login deve redirecionar para `accounts.google.com` com o client ID e o redirect acima, sem expor o segredo. Falhas no callback registram somente um código técnico, por exemplo `google_token_exchange_failed` ou `invalid_google_credential`; tokens, códigos de autorização, e-mails e valores de secrets nunca devem ir para o journal.

Depois de alterar o `.env`, valide a configuração com `docker compose config` e reconstrua somente o serviço principal. Não é necessário reiniciar Caddy ou o serviço legado.
