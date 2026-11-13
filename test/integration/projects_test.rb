require "test_helper"

class ProjectsTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "projects@example.test")
    sign_in_as(@account)
  end

  def create_project!(**attributes)
    @account.projects.create!(attributes)
  end

  test "projects page presents filters, board and list views" do
    get projects_path

    assert_response :success
    assert_select "h1", "Projetos"
    assert_select "[data-project-filter]", 3
    assert_select "[data-project-view-button]", 2
    assert_select "a[href='#{new_project_path}']", text: /Novo projeto/
  end

  test "projects page derives board status from its current stage and delivery" do
    create_project!(project_type: "case", title: "Case em andamento")
    create_project!(project_type: "case", title: "Case em revisão", current_stage: "review_report")
    delivered = create_project!(project_type: "case", title: "Case entregue", current_stage: "review_report")
    delivered.deliveries = { "report" => { "delivered" => true } }
    delivered.save!

    get projects_path

    assert_response :success
    assert_select "[data-project-column='in-progress'] [data-project-card]", count: 1
    assert_select "[data-project-column='review'] [data-project-card]", count: 1
    assert_select "[data-project-column='delivered'] [data-project-card]", count: 1
    assert_select "[data-project-card][data-project-kind='case'][data-project-status='in-progress']", count: 2
    assert_select ".agenda-panel", count: 0
  end

  test "shows the logged-in dashboard at the root" do
    get root_path

    assert_response :success
    assert_select "h1", "Início"
    assert_select "[data-project-view]", count: 0
    assert_select "h2", "Começando os trabalhos"
  end

  test "dashboard lists upcoming deliveries from project workflow fields" do
    date = 10.days.from_now.to_date
    create_project!(
      project_type: "case",
      title: "Entrega próxima",
      fields: { "report_delivery_date" => date.iso8601 }
    )

    get root_path

    assert_response :success
    assert_select ".delivery-item", text: /Relatório/
    assert_select ".delivery-item", text: /em 10 dias/
  end

  test "quick creation saves the chosen first delivery date on the matching workflow field" do
    date = 3.weeks.from_now.to_date.iso8601

    assert_difference("Project.count", 1) do
      post projects_path, params: { project: { project_type: "case", delivery_date: date } }
    end
    assert_equal date, Project.order(:id).last.fields["report_delivery_date"]

    assert_difference("Project.count", 1) do
      post projects_path, params: { project: { project_type: "paper_project", delivery_date: date } }
    end
    assert_equal date, Project.order(:id).last.fields["paper_project_delivery_date"]
  end

  test "creates a case and opens the first original stage" do
    @account.update_profile!(
      name: "Ana Estudante",
      profile: {
        "disciplines" => [ "Direito Civil" ],
        "teachers" => [ "Professora Exemplo" ],
        "period" => "7",
        "shift" => "noturno"
      }
    )

    assert_difference("Project.count", 1) do
      post projects_path, params: { project: { project_type: "case" } }
    end

    project = Project.order(:id).last
    assert_not_includes project.fields, "author"
    assert_equal Date.current.year.to_s, project.fields["year"]
    assert_equal "7", project.fields["period"]
    assert_equal "noturno", project.fields["shift"]
    assert_redirected_to project_path(project, stage: "identification")
    follow_redirect!
    assert_select "h2#stage-title", "Identificação"
    assert_select "textarea[name='project[fields][authors]']", count: 0
    assert_select "input[name='project[fields][partner]']"
    assert_select "select[name='project[fields][discipline]'] option", text: "Direito Civil"
    assert_select "select[name='project[fields][teacher]'] option", text: "Professora Exemplo"
    assert_select "select[name='project[fields][period]'] option[selected][value='7']"
    assert_select "select[name='project[fields][shift]'] option[selected][value='noturno']"
    assert_select "input[name='project[fields][year]'][value='#{Date.current.year}']"
  end

  test "reuses the decision alternatives in step 2.2 without duplicate input fields" do
    project = create_project!(
      project_type: "case",
      fields: { decision_a: "Texto da alternativa A", decision_b: "Texto da alternativa B" }
    )

    get project_path(project, stage: "thesis_argumentation")

    assert_response :success
    assert_select "h2#stage-title", "2.2 · Argumentação das alternativas"
    assert_select "textarea[name='project[fields][thesis_a]']", count: 0
    assert_select "textarea[name='project[fields][thesis_b]']", count: 0
    assert_select "label.alternative-title", count: 2
    assert_equal 1, response.body.scan("Texto da alternativa A").length
    assert_equal 1, response.body.scan("Texto da alternativa B").length
  end

  test "step 2.2 offers a text area for the argumentation of each alternative" do
    project = create_project!(
      project_type: "case",
      fields: { decision_a: "Texto da alternativa A", decision_b: "Texto da alternativa B" }
    )

    get project_path(project, stage: "thesis_argumentation")

    assert_response :success
    assert_select "textarea[name='project[fields][argument_a]']", count: 1
    assert_select "textarea[name='project[fields][argument_b]']", count: 1
    assert_select "textarea[name='project[fields][argument_a]'][aria-describedby='hint-argument_a']", count: 1
    assert_select "label.alternative-title", count: 2
  end

  test "debate step shows its before and after groups as headings" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "debate")

    assert_response :success
    assert_select "h3.field-group-title", count: 2
  end

  test "consumes one project credit atomically and blocks creation without credits" do
    @account.update!(project_limit: 1, project_used: 0)
    post projects_path, params: { project: { project_type: "case" } }

    assert_response :redirect
    assert_equal 1, @account.reload.project_used
    assert_equal 0, @account.project_credits_remaining

    post projects_path, params: { project: { project_type: "case" } }

    assert_response :unprocessable_entity
    assert_select ".alert", text: /créditos de projeto/
  end

  test "renders one step while retaining the complete route navigation" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "description")

    assert_response :success
    assert_select "h2#stage-title", "1 · Descrição do caso"
    assert_select "textarea[name='project[fields][facts]']"
    assert_select "nav.editor-stage-list button", count: 10
    assert_select "textarea[name='project[fields][dissertation_intro]']", count: 0
  end

  test "renders contextual AI controls without provider names in the panel" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "description")

    assert_response :success
    assert_select "[data-ai-panel][data-action-url='/projects/#{project.id}/ai/action']"
    assert_select "button[data-ai-action='proposal_chat']"
    assert_select "button[data-ai-action='suggest_problem']"
    assert_select "button[data-jev-section-action]"
    assert_select "button[data-jev-report]"
    assert_select "select[data-jev-section-select] option", count: 5
    assert_select "[data-ai-panel]", text: /JEV|DeepSeek|TypeSafe/, count: 0
  end

  test "does not render Case-only JEV controls for a Paper" do
    project = create_project!(project_type: "paper_project")

    get project_path(project, stage: "paper_identification")

    assert_response :success
    assert_select "[data-ai-panel]"
    assert_select "[data-jev-section-action]", count: 0
    assert_select "[data-jev-report]", count: 0
  end

  test "renders only fixed delivery date fields for Case phases" do
    project = create_project!(project_type: "case")

    {
      "identification" => "report_delivery_date",
      "debate" => "debate_delivery_date",
      "dissertation" => "dissertation_delivery_date"
    }.each do |stage, field|
      get project_path(project, stage:)

      assert_response :success
      assert_select "input[type='date'][name='project[fields][#{field}]']"
      assert_select "[data-planning-open]", count: 0
      assert_select "[data-add-task]", count: 0
    end
  end

  test "renders and saves the single dissertation field" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "dissertation")

    assert_response :success
    assert_select "textarea[name='project[fields][dissertation]']", count: 1
    assert_select "textarea[name='project[fields][dissertation_intro]']", count: 0
    assert_select "textarea[name='project[fields][dissertation_conclusion]']", count: 0
    assert_select "[data-collection-add]", count: 0

    patch project_path(project, stage: "dissertation"), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "dissertation",
        fields: { dissertation: "Texto único da dissertação." }
      }
    }

    assert_redirected_to project_path(project, stage: "dissertation")
    assert_equal "Texto único da dissertação.", project.reload.fields["dissertation"]
    assert_empty project.development_sections
  end

  test "exposes saved document previews and PDF export for every Case phase" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "description")

    assert_response :success
    assert_select "a[href='#{export_project_path(project, format: :html, phase: :report)}']", text: "Prévia do relatório"
    assert_select "a[href='#{export_project_path(project, format: :html, phase: :debate)}']", text: "Prévia do debate"
    assert_select "a[href='#{export_project_path(project, format: :html, phase: :dissertation)}']", text: "Prévia da dissertação"
    assert_select "a[href='#{export_project_path(project, format: :pdf, phase: :report)}']", text: "Baixar PDF do relatório"
  end

  test "exposes HTML preview and PDF export for Papers" do
    project = create_project!(project_type: "paper_final")

    get project_path(project, stage: "paper_final_identity")

    assert_response :success
    assert_select "a[href='#{export_project_path(project, format: :html)}']", text: "Prévia HTML"
    assert_select "a[href='#{export_project_path(project, format: :pdf)}']", text: "Baixar PDF"
  end

  test "saves only the three fixed Case delivery dates" do
    project = create_project!(project_type: "case")

    patch project_path(project, stage: "review_report"), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "review_report",
        fields: {
          report_delivery_date: "2026-11-28",
          debate_delivery_date: "2026-12-01",
          dissertation_delivery_date: "2026-02-30",
          arbitrary_deadline: "2026-12-15"
        }
      }
    }

    assert_redirected_to project_path(project, stage: "review_report")
    project.reload
    assert_equal "2026-11-28", project.fields["report_delivery_date"]
    assert_equal "2026-12-01", project.fields["debate_delivery_date"]
    assert_equal "", project.fields["dissertation_delivery_date"]
    assert_not_includes project.fields, "arbitrary_deadline"
  end

  test "saves answers and checklist state with a revision snapshot" do
    project = create_project!(project_type: "case")

    patch project_path(project, stage: "description"), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "description",
        fields: { facts: "Fatos relevantes", problem: "Qual solução jurídica?" },
        checks: { "facts-original" => "1" }
      },
      go_to_stage: "decisions"
    }

    assert_redirected_to project_path(project, stage: "decisions")
    project.reload
    assert_equal "Fatos relevantes", project.fields["facts"]
    assert_equal true, project.checks["facts-original"]
    assert_equal 1, project.lock_version
    assert_equal 2, project.revisions.count
  end

  test "rejects a stale edit without overwriting the newer revision" do
    project = create_project!(project_type: "case")
    stale_version = project.lock_version
    patch project_path(project), params: { project: { lock_version: stale_version, current_stage: "identification", fields: { title: "Atual" } } }
    assert_response :redirect

    patch project_path(project), params: { project: { lock_version: stale_version, current_stage: "identification", fields: { title: "Antigo" } } }

    assert_response :conflict
    assert_equal "Atual", project.reload.fields["title"]
  end

  test "converts a paper project to the final without losing its project data" do
    project = create_project!(
      project_type: "paper_project",
      fields: { title: "Pesquisa", hypothesis: "Hipótese inicial" }
    )

    patch paper_mode_project_path(project), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "review_paper",
        fields: { justification: "Relevância" }
      }
    }

    assert_redirected_to project_path(project, stage: "paper_final_identity")
    project.reload
    assert_equal "paper_final", project.project_type
    assert_equal "Pesquisa", project.fields["title"]
    assert_equal "Hipótese inicial", project.fields["hypothesis"]
    assert_equal "Relevância", project.fields["justification"]
  end

  test "does not allow starting a paper final directly or switching it back" do
    post projects_path, params: { project: { project_type: "paper_final" } }
    assert_response :unprocessable_entity

    project = create_project!(project_type: "paper_project")
    patch paper_mode_project_path(project), params: {
      project: { lock_version: project.lock_version, current_stage: "paper_final_identity" }
    }
    assert_response :redirect
    project.reload

    patch paper_mode_project_path(project), params: { project: { lock_version: project.lock_version } }
    assert_response :conflict
    assert_equal "paper_final", project.reload.project_type
  end

  test "registers delivery from the review stage" do
    project = create_project!(project_type: "case")

    patch project_path(project, stage: "review_report"), params: {
      project: { lock_version: project.lock_version, current_stage: "review_report" },
      mark_delivered: "1"
    }

    assert_redirected_to project_path(project, stage: "review_report")
    assert project.reload.delivered?(project.section_for("review_report"))
  end

  test "saving paper dates in the wrong order warns without blocking the save" do
    account = create_test_account(email: "paper-dates@example.test")
    account.update!(terms_accepted: true, ai_consent: true)
    sign_in_as(account)
    project = account.projects.create!(project_type: "paper_project", fields: {})

    patch paper_mode_project_path(project), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "review_paper",
        fields: { paper_project_delivery_date: "2026-11-20" }
      }
    }

    assert_response :redirect
    project.reload

    patch project_path(project, stage: "paper_final_identity"), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "paper_final_identity",
        fields: { paper_final_delivery_date: "2026-10-01" }
      }
    }

    assert_response :redirect
    assert_equal "A entrega do paper final é antes do projeto de paper.", flash[:alert]
    assert_equal "2026-10-01", project.reload.fields["paper_final_delivery_date"]
  end
end
