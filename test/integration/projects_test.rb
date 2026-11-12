require "test_helper"

class ProjectsTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "projects@example.test")
    sign_in_as(@account)
  end

  def create_project!(**attributes)
    @account.projects.create!(attributes)
  end

  test "projects page presents the project entry point" do
    get projects_path

    assert_response :success
    assert_select "h1", "Transforme uma ideia em um trabalho bem estruturado."
    assert_select "a[href='#{new_project_path}']", "Começar um trabalho"
  end

  test "projects page shows upcoming and overdue task deadlines" do
    create_project!(
      project_type: "case",
      title: "Case de teste",
      schedule: {
        "tasks" => [
          { "id" => "overdue", "title" => "Entregar rascunho", "date" => "2020-01-01" },
          { "id" => "future", "title" => "Revisar argumentos", "date" => "2099-12-31" }
        ]
      }
    )

    get projects_path

    assert_response :success
    assert_select "h2#agenda-title", "Próximos prazos de tarefas"
    assert_select ".agenda-item", count: 2
    assert_select ".agenda-item.is-overdue", text: /Atrasada/
    assert_select ".agenda-item", text: /Revisar argumentos/
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
    assert_equal "Ana Estudante", project.fields["author"]
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
    assert_select ".reused-decision", count: 2
    assert_includes response.body, "Texto da alternativa A"
    assert_includes response.body, "Texto da alternativa B"
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
    assert_select "nav.step-nav button", count: 10
    assert_select "textarea[name='project[fields][dissertation_intro]']", count: 0
  end

  test "renders contextual AI controls and the separate JEV assessment for Cases" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "description")

    assert_response :success
    assert_select "[data-ai-panel][data-action-url='/projects/#{project.id}/ai/action']"
    assert_select "button[data-ai-action='proposal_chat']"
    assert_select "button[data-ai-action='suggest_problem']"
    assert_select "button[data-jev-section-action]"
    assert_select "button[data-jev-report]"
    assert_select "select[data-jev-section-select] option", count: 5
  end

  test "does not render Case-only JEV controls for a Paper" do
    project = create_project!(project_type: "paper_project")

    get project_path(project, stage: "paper_identification")

    assert_response :success
    assert_select "[data-ai-panel]"
    assert_select "[data-jev-section-action]", count: 0
    assert_select "[data-jev-report]", count: 0
  end

  test "renders the planning dialog with task-specific deadlines" do
    project = create_project!(project_type: "case")

    get project_path(project, stage: "description")

    assert_response :success
    assert_select "button[data-planning-open] span:first-child", "Planejar este trabalho"
    assert_select "dialog#project-planning"
    assert_select "input[name='project[schedule][tasks][INDEX_PLACEHOLDER][date]']"
    assert_select "[data-add-task]", text: "Adicionar tarefa"
    assert_select "[data-add-suggested-tasks]", count: 0
    assert_select "input[name^='project[schedule][report_date]']", count: 0
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

  test "saves only task delivery dates and completion state" do
    project = create_project!(project_type: "paper_project")

    patch project_path(project, stage: "paper_project_identity"), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: "paper_identification",
        schedule: {
          tasks: {
            "0" => { id: "task-1", title: "Revisar o projeto", date: "2026-10-29", done: "1" }
          }
        }
      }
    }

    assert_redirected_to project_path(project, stage: "paper_identification")
    project.reload
    assert_equal [ "tasks" ], project.schedule.keys
    assert_equal true, project.schedule["tasks"].first["done"]
    assert_equal "2026-10-29", project.schedule["tasks"].first["date"]
  end

  test "allows removing every task from the schedule" do
    project = create_project!(
      project_type: "case",
      schedule: { tasks: [ { id: "task-1", title: "Revisar", date: "2026-10-29" } ] }
    )

    patch project_path(project), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: project.current_stage,
        schedule: { tasks: { clear: "" } }
      }
    }

    assert_redirected_to project_path(project, stage: project.current_stage)
    assert_empty project.reload.schedule["tasks"]
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
end
