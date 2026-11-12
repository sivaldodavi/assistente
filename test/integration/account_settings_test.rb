require "test_helper"

class AccountSettingsTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "settings@example.test", name: "Settings")
    sign_in_as(@account)
  end

  test "profile details are saved separately from account identity" do
    post account_update_profile_path, params: {
      name: "Nome Atualizado",
      institution: "Universidade",
      course: "Direito",
      period: "10",
      shift: "noturno",
      disciplines: "Pesquisa\nÉtica\n",
      teachers: "Docente A\nDocente B\n"
    }

    assert_redirected_to account_settings_path(saved: "profile")
    @account.reload
    assert_equal "Nome Atualizado", @account.name
    assert_equal "Universidade", @account.profile["institution"]
    assert_equal "10", @account.profile["period"]
    assert_equal "noturno", @account.profile["shift"]
    assert_equal %w[Pesquisa Ética], @account.profile["disciplines"]
    assert_equal [ "Docente A", "Docente B" ], @account.profile["teachers"]
    assert_not_includes @account.profile, "discipline"
    assert_not_includes @account.profile, "professor"
  end

  test "profile offers all supported periods and both shifts without duplicate single-value fields" do
    get account_settings_path

    assert_response :success
    assert_select "select[name='period'] option", count: 11
    assert_select "select[name='shift'] option", count: 3
    assert_select "input[name='discipline']", count: 0
    assert_select "input[name='professor']", count: 0
  end

  test "terms and AI consent are recorded independently" do
    post account_accept_terms_path, params: { accept: "on" }

    assert_redirected_to account_settings_path(saved: "terms")
    @account.reload
    assert @account.terms_accepted?
    assert_not @account.ai_consent?
    assert_equal Account::TERMS_VERSION, @account.terms_version
    assert_not_nil @account.terms_accepted_at
  end

  test "account deletion requires confirmation and removes owned data" do
    project = @account.projects.create!(project_type: "case")
    source = @account.sources.create!(title: "Referência")

    post account_delete_path, params: { confirmation: "wrong@example.test" }
    assert_redirected_to account_settings_path(anchor: "delete-account")
    assert Account.exists?(@account.id)

    post account_delete_path, params: { confirmation: @account.email }

    assert_redirected_to root_path
    assert_not Account.exists?(@account.id)
    assert_not Project.exists?(project.id)
    assert_not Source.exists?(source.id)
    get account_settings_path
    assert_redirected_to login_path
  end
end
