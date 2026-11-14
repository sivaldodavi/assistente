# Skills Operacionais do Projeto (.gemini/skills/)

Este diretório contém as skills padronizadas para agentes e IAs que interagem com o **Assistente Acadêmico**.

## Como utilizar

- **Carregamento Automático**: Ferramentas compatíveis com o padrão Antigravity/Gemini carregam automaticamente as skills deste diretório com a prioridade mais alta de projeto.
- **Cópia Local**: Caso uma IA esteja rodando em um ambiente isolado sem acesso automático a workspaces, ela pode copiar este diretório para o seu repositório local de skills (`~/.gemini/config/skills/`).
- **Atualização**: Qualquer aprimoramento nos procedimentos operacionais ou comandos deve ser comitado e sincronizado tanto na skill deste repositório quanto na cópia local da IA.

## Skills Disponíveis

* **`assistente-academico`**: Procedimentos operacionais para deploy com `bin/ops`, suíte de testes em Docker, health check, fluxo de branch temporária para propostas e SemVer.
