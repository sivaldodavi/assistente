# Compartilhamento e administração

## Privacidade por padrão

Cada projeto começa privado. O proprietário pode autorizar visualização administrativa e, separadamente, comentários administrativos. A segunda autorização não é ativada quando a primeira é salva sem a segunda.

Revogar visualização impede novas aberturas administrativas. O texto acadêmico permanece no snapshot do proprietário; comentários ficam em `project_comments` e nunca são misturados aos campos do projeto.

## Administração

A aplicação não promove o primeiro usuário automaticamente. Administradores são definidos por `ASSISTENTE_V2_ADMIN_EMAILS`, uma lista de e-mails configurada fora do Git. A rota administrativa exige sessão e essa configuração.

O administrador vê apenas projetos com `allow_admin_view=1` e abre uma apresentação somente leitura. Se permitido, pode escrever comentário separado. Não existe endpoint administrativo para salvar o snapshot acadêmico do proprietário.

## Testes

Os testes criam proprietário e administrador fictícios, verificam a revogação implícita por padrão, isolamento de conta e comentário separado. Nenhuma permissão é herdada do banco legado.
