require "test_helper"

class DashboardTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "dashboard@example.test")
    sign_in_as(@account)
  end

  test "metrics filters assessment history by period without combining different rubrics" do
    project = @account.projects.create!(project_type: "case")
    revision = project.revisions.sole
    assessment = @account.jev_assessments.create!(
      project:,
      project_revision: revision,
      stage: "case_report",
      rubric_version: JevRubric::VERSION,
      model: "fake-jev",
      result: { "stage" => "case_report", "expected_points" => 2.4, "assessable_points" => 3.5 }
    )
    assessment.update_column(:created_at, 120.days.ago)

    get metrics_path, params: { period: "90" }

    assert_response :success
    assert_select "select[name='period'] option[selected][value='90']"
    assert_select ".dashboard-metrics div:nth-child(3) strong", text: "0"
    assert_select ".dashboard-metrics div:nth-child(3) span", text: "avaliações no período"
    assert_select ".dashboard-assessment-list", count: 0

    get metrics_path, params: { period: "all" }

    assert_response :success
    assert_select ".dashboard-metrics div:nth-child(3) strong", text: "1"
    assert_select ".dashboard-metrics div:nth-child(3) span", text: "avaliações no período"
    assert_select ".dashboard-assessment-list", text: /2.4\/3.5 pontos indicativos/
    assert_includes response.body, "não são somados nem comparados"
  end
end
