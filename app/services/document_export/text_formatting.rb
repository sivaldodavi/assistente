class DocumentExport
  # Escape e formatação de texto para Markdown, Typst e HTML.
  module TextFormatting
    MARKDOWN_ESCAPABLE = "\\`*_{}[]<>()#+.!|~&+-".freeze

    def text(value)
      return "" unless value.is_a?(String)

      value.delete("\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F").gsub("\r\n", "\n").tr("\r", "\n")
    end

    def typst_literal(value)
      JSON.generate(text(value))
    end

    def yaml_typst_scalar(value)
      JSON.generate(typst_literal(value)[1...-1])
    end

    def markdown_text(value)
      text(value).each_char.map { |character| MARKDOWN_ESCAPABLE.include?(character) ? "\\#{character}" : character }.join
    end

    def paragraphs(value)
      text(value).strip.split(/\n[ \t]*\n+/).filter_map do |paragraph|
        next if paragraph.strip.empty?

        paragraph.split("\n").map { |line| markdown_text(line) }.join("  \n")
      end.join("\n\n")
    end

    def html_paragraphs(value)
      parts = text(value).strip.split(/\n[ \t]*\n+/).filter_map(&:presence)
      return '<p class="empty">Não preenchido.</p>' if parts.empty?

      parts.map { |part| "<p>#{escape(part.strip).gsub("\n", "<br>")}</p>" }.join
    end

    def escape(value)
      ERB::Util.html_escape(value.to_s).to_s
    end

    def yaml_list(name, values)
      return "#{name}: []" if values.empty?

      "#{name}:\n" + values.map { |value| "  - #{yaml_typst_scalar(value)}" }.join("\n")
    end

    def raw_typst(code)
      "```{=typst}\n#{code.strip}\n```\n"
    end
  end
end
