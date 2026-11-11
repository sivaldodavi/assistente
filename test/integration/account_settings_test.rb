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
      discipline: "Metodologia",
      professor: "Orientação",
      disciplines: "Pesquisa\nÉtica\n",
      teachers: "Docente A\nDocente B\n"
    }

    assert_redirected_to account_settings_path(saved: "profile")
    @account.reload
    assert_equal "Nome Atualizado", @account.name
    assert_equal "Universidade", @account.profile["institution"]
    assert_equal %w[Pesquisa Ética], @account.profile["disciplines"]
    assert_equal [ "Docente A", "Docente B" ], @account.profile["teachers"]
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
