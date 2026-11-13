require "test_helper"

class SourcesTest < ActionDispatch::IntegrationTest
  test "adds, edits, lists, and deletes a source within its owner's library" do
    owner = create_test_account(email: "library-owner@example.test")
    sign_in_as(owner)
    get library_path
    assert_response :success
    assert_select "h1", "Biblioteca Pessoal"
    assert_select ".app-shell"
    assert_select "header.site-header", count: 0

    assert_difference("Source.count", 1) do
      post sources_path, params: {
        source: {
          title: "Teoria do Direito",
          author: "Autoria Exemplo",
          kind: "book",
          reference: "São Paulo, 2026",
          notes: "Anotação privada."
        }
      }
    end
    source = owner.sources.sole
    assert_redirected_to library_path(saved: "source")
    get library_path
    assert_includes response.body, "Teoria do Direito"
    assert_select ".library-card details summary", text: "Fichamento"

    patch source_path(source), params: {
      source: { title: "Teoria revisada", author: "Autoria revisada", kind: "article", reference: "Revista, 2026", notes: "Fichamento revisado." }
    }
    assert_redirected_to library_path(saved: "source-updated")
    source.reload
    assert_equal "article", source.kind
    assert_equal "Fichamento revisado.", source.notes

    delete source_path(source)
    assert_response :no_content
    assert_not Source.exists?(source.id)
  end

  test "does not expose or mutate another account's source" do
    owner = create_test_account(email: "library-private@example.test")
    source = owner.sources.create!(title: "Privada")
    other = create_test_account(email: "library-other@example.test")
    sign_in_as(other)

    get library_path
    assert_response :success
    assert_not_includes response.body, "Privada"
    get edit_source_path(source)
    assert_response :not_found
    patch source_path(source), params: { source: { title: "Tomada" } }
    assert_response :not_found
    post delete_source_path(source)
    assert_response :not_found
    assert_equal "Privada", source.reload.title
  end

  test "stores only source IDs owned by the account on a project" do
    owner = create_test_account(email: "source-link-owner@example.test")
    source = owner.sources.create!(title: "Fonte própria")
    other_account = create_test_account(email: "source-link-other@example.test")
    other_source = other_account.sources.create!(title: "Fonte alheia")
    sign_in_as(owner)
    project = owner.projects.create!(project_type: "case")
    stage_id = project.sections.find { |section| section["custom"] == "sources" }.fetch("id")

    patch project_path(project, stage: stage_id), params: {
      project: {
        lock_version: project.lock_version,
        current_stage: stage_id,
        source_ids: [ source.public_id, other_source.public_id ]
      }
    }

    assert_redirected_to project_path(project, stage: stage_id)
    assert_equal [ source.public_id ], project.reload.source_ids
  end
end
