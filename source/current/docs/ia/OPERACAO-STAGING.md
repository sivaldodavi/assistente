# Staging da aplicação no VPS

## Isolamento

O Compose de staging é opcional e usa o container `assistente-academico-staging`, a porta somente local `127.0.0.1:18080`, o diretório `/opt/servidor/data/assistente-academico-staging` e um arquivo de ambiente externo. Não monta o banco do legado, não usa o Compose principal, não altera Caddy e não inclui gateway de mensagens.

O staging serve para validação técnica antes de uma mudança. O domínio público já usa a aplicação principal; o staging não deve receber o callback OAuth de produção nem dados reais.

## Publicação do código

O bare repo principal fica em `/home/git/repos/assistente-academico.git` e alimenta o stagit. O checkout `/opt/servidor/work/assistente-academico` é apenas uma cópia de trabalho para inspeção e staging; o deploy do domínio extrai a referência diretamente do bare repository.

```sh
git clone /home/git/repos/assistente-academico.git /opt/servidor/work/assistente-academico
cd /opt/servidor/work/assistente-academico
git fetch --prune
git checkout main
git reset --hard origin/main
docker compose -f compose.staging.yml up -d --build
curl -fsS http://127.0.0.1:18080/healthz
docker compose -f compose.staging.yml ps
```

O arquivo `/opt/servidor/config/assistente-academico-staging.env` deve ser criado pelo operador com a chave de sessão e, quando necessário, caminhos de secrets montados. Ele não entra no Git. A imagem instala Quarto 1.10.19 e usa a extensão ABNT Typst portada do produto de referência; o teste técnico mínimo é `quarto render` de um QMD fictício para PDF.

## Critérios de validação

Testar HTTPS, Google OAuth, cookies, autosave/conflito, PDF com Quarto/Typst, IA com provedores falsos ou controlados, consumo de RAM e rollback. O staging não substitui a validação manual do serviço publicado e nunca deve compartilhar o banco do legado; o contato manual externo não é testado pelo aplicativo.
