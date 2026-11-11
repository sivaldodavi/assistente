require "test_helper"

class ExportsTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "exports@example.test")
    sign_in_as(@account)
  end

  test "serves an escaped HTML preview for an existing project" do
    project = @account.projects.create!(project_type: "case", fields: { "title" => "<img src=x>", "facts" => "Narrativa" })

    get export_project_path(project, format: "html")

    assert_response :success
    assert_equal "text/html; charset=utf-8", response.media_type + "; charset=utf-8"
    assert_includes response.body, "&lt;img src=x&gt;"
    assert_includes response.body, "Narrativa"
  end

  test "rejects unsupported export formats and Case phases" do
    project = @account.projects.create!(project_type: "case")

    get export_project_path(project, format: "doc")
    assert_response :bad_request

    get export_project_path(project, format: "html", phase: "unknown")
    assert_response :bad_request
  end
end
