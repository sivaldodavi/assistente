# Skills e Guias Operacionais do Projeto (docs/skills/)

Este diretório concentra exclusivamente **skills canônicas e permanentes** para orientar qualquer Inteligência Artificial (Claude, ChatGPT, Gemini, Copilot, Cursor, etc.) ou desenvolvedor humano no ciclo operacional do **Assistente Acadêmico**.

---

## 1. Política de Controle de Qualidade de Skills

Para evitar poluição do repositório com instruções obsoletas ou efêmeras, aplicam-se as seguintes regras de curadoria:

1. **Apenas Procedimentos Permanentes e Canônicos**:
   - Só devem ser mantidas aqui skills que ensinem rotinas recorrentes de infraestrutura, aplicação de patches, testes e releases.
   - **Proibições**: Instruções pontuais, scripts de migração descartáveis ou comandos temporários de depuração **NÃO** devem virar skills neste repositório.
2. **Ciclo de Atualização Recíproca**:
   - A IA que utilizar estas instruções pode carregá-las no seu contexto ou copiá-las para sua configuração local.
   - Caso o desenvolvedor solicite melhorias no fluxo operacional (como novos comandos de teste ou regras de deploy), a IA **deve atualizar a respectiva skill aqui no repositório**, garantindo paridade com sua cópia local.

---

## 2. Skills Canônicas Disponíveis

* **[`assistente-academico`](assistente-academico/SKILL.md)**: 
  - **Função**: Guia definitivo de aplicação e conferência de patches, execução da suíte de testes em Docker, linter RuboCop, automação via `bin/ops`, health check em produção, convenção de branches temporárias para propostas e versionamento SemVer com tags anotadas.
