namespace :db do
  namespace :seed do
    desc "Cria dados de demonstração (Projetos de Case e Paper) para testes e preview"
    task demo: :environment do
      account = Account.find_by(role: "admin") || Account.first
      if account.nil?
        puts "Nenhuma conta encontrada. Faça login ou crie uma conta antes de rodar os dados de demonstração."
        exit 1
      end

      puts "Criando projetos de demonstração para a conta: #{account.email}..."

      # 1. Projeto de Demonstração: Case Jurídico
      case_project = account.projects.find_or_create_by!(title: "Case Modelo: Análise de Contrato Eletrônico") do |p|
        p.project_type = "case"
        p.fields = {
          client_name: "Empresa Alfa Tecnologia Ltda.",
          facts: "A empresa contratou fornecimento de serviços em nuvem com cláusula de renovação automática sem aviso prévio.",
          problem: "A validade e abusividade da rescisão contratual com multa integral em contratação eletrônica B2B.",
          decision_a: "Acolher a aplicação integral da multa rescisória com base na autonomia da vontade empresarial.",
          decision_b: "Reduzir equitativamente a penalidade com fulcro no art. 413 do Código Civil.",
          argument_a: "Empresas com capacidade econômico-financeira devem honrar os termos pactuados livremente.",
          argument_b: "A penalidade excessiva desequilibra o contrato e configura enriquecimento sem causa.",
          report_delivery_date: (Date.current + 7.days).iso8601,
          debate_delivery_date: (Date.current + 14.days).iso8601,
          dissertation_delivery_date: (Date.current + 21.days).iso8601
        }
      end

      # 2. Projeto de Demonstração: Paper Acadêmico
      paper_project = account.projects.find_or_create_by!(title: "Paper Modelo: Inteligência Artificial no Processo Civil") do |p|
        p.project_type = "paper_project"
        p.fields = {
          theme: "Impacto das decisões automatizadas na garantia do contraditório judicial.",
          problem: "Em que medida o uso de algoritmos preditivos compromete a motivação das decisões judiciais?",
          justification: "A crescente digitalização dos tribunais exige parâmetros éticos e normativos claros.",
          general_objective: "Analisar a compatibilidade entre decisões por IA e o art. 489 do CPC.",
          methodology: "Pesquisa bibliográfica e análise jurisprudencial comparada."
        }
      end

      puts "Projetos de demonstração prontos com sucesso:"
      puts " - Case: #{case_project.title} (ID: #{case_project.id})"
      puts " - Paper: #{paper_project.title} (ID: #{paper_project.id})"
    end
  end
end
