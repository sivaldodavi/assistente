# Provedores externos de IA

## Fronteira

DeepSeek, Gemini e JEV/Typesafe são serviços externos atrás de adaptadores em `app/services/providers.py`. Rotas e domínio não montam `urllib.Request` diretamente.

Os adaptadores recebem a chave, a URL, o modelo, o timeout e um transporte injetável. O transporte falso é usado na suíte; testes não fazem chamadas reais.

## DeepSeek

O contrato envia `model`, `messages`, `response_format` JSON, `max_tokens` e `stream: false` ao endpoint configurado. A resposta precisa ter uma única escolha com conteúdo JSON objeto. O adaptador devolve modelo, resultado estruturado e uso; não interpreta a regra acadêmica.

### Timeouts configuráveis

- `DEEPSEEK_TIMEOUT` (padrão 30s) - timeout para chamadas DeepSeek
- Configurável via construtor: `DeepSeekClient(api_key, ..., timeout=30)`

## JEV/Typesafe

O contrato envia `state`, `model` e `questions` ao endpoint configurado. A resposta precisa conter `answers` como objeto. A validação detalhada de rubric, itens permitidos, confiança e persistência de uso pertence ao serviço de aplicação que chamará o adaptador, não ao transporte.

Na aplicação, a rota de validação monta perguntas fixas a partir do campo permitido e do problema do próprio projeto. O cliente não escolhe instruções JEV arbitrárias. O resultado é devolvido para revisão e não é salvo automaticamente no snapshot.

### Timeouts configuráveis

- `JEV_TIMEOUT` (padrão 60s) - timeout para chamadas JEV/Typesafe
- Configurável via construtor: `JevClient(api_key, ..., timeout=60)`

## Gemini

`GeminiClient` usa a API REST `generateContent`, cabeçalho `x-goog-api-key` e `responseMimeType: application/json`. A resposta é normalizada para o mesmo contrato JSON do DeepSeek e validada localmente antes de chegar ao editor.

Gemini é fallback técnico da recomendação jurídica contextual, não segundo resultado concorrente. Só é chamado uma vez se o DeepSeek falhar por timeout, rede, 408, 429, 5xx ou resposta JSON inválida. Não há fallback em 401, 402, falta de consentimento, falta de catálogo ou configuração ausente.

### Timeouts configuráveis

- `GEMINI_TIMEOUT` (padrão 30s) - timeout para chamadas Gemini
- Configurável via construtor: `GeminiClient(api_key, ..., timeout=30)`

## Timeout base

- `PROVIDER_TIMEOUT` (padrão 30s) - timeout base herdado por todos os provedores

## Secrets

A chave pode vir de variável de ambiente ou de arquivo indicado por `*_API_KEY_FILE`, compatível com secrets montados pelo Docker. O valor não é impresso, salvo no banco, enviado ao frontend ou incluído em exceções.

Para produção, o caminho reservado para a chave Gemini é `/opt/servidor/secrets/assistente-academico/gemini_api_key`, com permissão `0400` para UID/GID `10001:10001`. O Compose monta esse arquivo como `/run/secrets/gemini_api_key` e a aplicação o lê por `GEMINI_API_KEY_FILE`. Se o arquivo estiver vazio, o DeepSeek continua funcionando e somente o fallback Gemini ficará indisponível. Nunca coloque a chave no repositório, no banco, no `.env` versionado ou em uma mensagem do chat.

Depois de preencher o arquivo, reconstrua somente o serviço do Assistente com o procedimento operacional documentado. Não é necessário alterar o código nem o frontend.

## Falhas

401/403 vira erro de configuração; 429/529, 408, 5xx, timeout e erro de rede são falhas temporárias elegíveis ao fallback somente na recomendação jurídica. Corpo de erro do provedor não é registrado no log.

## Limites do produto

Nenhum adaptador libera sozinho uma chamada para um projeto. Consentimento de IA, reserva de uso, contexto mínimo, ação permitida, validação da resposta e registro de uso serão contratos separados. O provedor nunca decide o conteúdo do projeto sem confirmação explícita do usuário.
