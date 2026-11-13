require "test_helper"

class DocumentExportRendererTest < ActiveSupport::TestCase
  test "reports Quarto as unavailable when the configured binary does not exist" do
    project = Project.new(project_type: "case", fields: { "title" => "Relatório", "decision_a" => "Alternativa A." })
    original = ENV["QUARTO_BINARY"]
    ENV["QUARTO_BINARY"] = "/nonexistent/quarto-binary"

    error = assert_raises(DocumentExport::QuartoUnavailable) { DocumentExport.render_pdf(project) }
    assert_includes error.message, "não está disponível"
  ensure
    ENV["QUARTO_BINARY"] = original
  end

  test "reports busy when all render slots are in use" do
    project = Project.new(project_type: "case", fields: { "title" => "Relatório", "decision_a" => "Alternativa A." })
    renderer = DocumentExport::QuartoRenderer

    with_singleton_stub(renderer, :executable_path, "/bin/sh") do
      renderer.instance_variable_set(:@active_renders, renderer::MAX_CONCURRENT_RENDERS)
      begin
        assert_raises(DocumentExport::QuartoBusy) { DocumentExport.render_pdf(project) }
      ensure
        renderer.instance_variable_set(:@active_renders, 0)
      end
    end
  end

  private

  def with_singleton_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end
end
