require "json"

class AcademicWorkflow
  WORKFLOWS = JSON.parse(Rails.root.join("config/academic_workflows.json").read)
  COMMON_FIELD_LIMITS = {
    "course" => 160,
    "city" => 160,
    "author" => 1_200,
    "authors" => 1_200,
    "dissertation_author" => 160
  }.freeze
  LEGACY_FIELD_ALIASES = {
    "decision_a" => "thesis_a",
    "decision_b" => "thesis_b"
  }.freeze
  DELIVERY_KEYS = %w[report dissertation paper_project paper_final].freeze

  class << self
    def types
      WORKFLOWS.keys
    end

    def editable_types
      %w[case paper_project]
    end

    def sections(project_type)
      WORKFLOWS.fetch(project_type.to_s) { raise ArgumentError, "Roteiro acadêmico inválido" }
    end

    def first_stage_id(project_type)
      sections(project_type).first.fetch("id")
    end

    def field_rules(project_type)
      source_types = project_type.to_s == "paper_final" ? %w[paper_project paper_final] : [ project_type.to_s ]
      rules = source_types.flat_map { |type| sections(type).flat_map { |section| section.fetch("fields", []) } }
      rules.index_by { |field| field.fetch("id") }.merge(
        COMMON_FIELD_LIMITS.transform_values { |limit| { "limit" => limit } }
      )
    end

    def normalize_fields(project_type, raw)
      source = hash_value(raw)
      field_rules(project_type).each_with_object({}) do |(field_id, rule), fields|
        value = source[field_id]
        value = source[LEGACY_FIELD_ALIASES[field_id]] if value.blank? && LEGACY_FIELD_ALIASES.key?(field_id)
        value = value.nil? ? "" : value.to_s.strip
        limit = Integer(rule["limit"] || 16_000)
        value = value[0, limit]
        value = normalize_date(value) if rule["type"] == "date"

        options = rule["options"]
        if options.is_a?(Array) && !options.empty?
          allowed = options.map { |option| option.first.to_s }
          value = "" unless allowed.include?(value)
        end

        fields[field_id] = value
      end
    end

    def normalize_checks(project_type, raw)
      allowed = sections(project_type).flat_map { |section| section.fetch("checks", []).map(&:first) }.uniq
      source = hash_value(raw)
      allowed.index_with { |key| truthy?(source[key]) }
    end

    def normalize_criteria(raw)
      rows(raw).first(40).filter_map do |item|
        values = hash_value(item)
        criterion = {
          "id" => bounded(values["id"].presence || SecureRandom.uuid, 80),
          "title" => bounded(values["title"], 180),
          "definition" => bounded(values["definition"], 3_000),
          "basis" => bounded(values["basis"], 1_000)
        }
        criterion unless criterion.values_at("title", "definition", "basis").all?(&:blank?)
      end
    end

    def normalize_development_sections(raw)
      rows(raw).first(20).filter_map do |item|
        values = hash_value(item)
        section = {
          "id" => bounded(values["id"].presence || SecureRandom.uuid, 80),
          "title" => bounded(values["title"], 240),
          "body" => bounded(values["body"], 30_000)
        }
        section if section["title"].present? || section["body"].present?
      end
    end

    def normalize_source_ids(raw)
      Array(raw).filter_map do |value|
        id = value.to_s
        id if id.match?(/\A[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/i)
      end.uniq.first(100)
    end

    def normalize_deliveries(raw)
      source = hash_value(raw)
      DELIVERY_KEYS.each_with_object({}) do |key, result|
        delivery = hash_value(source[key])
        next unless truthy?(delivery["delivered"])

        result[key] = { "delivered" => true, "at" => Integer(delivery["at"] || 0) }
      rescue ArgumentError, TypeError
        next
      end
    end

    def progress(project_type, fields, phase)
      sections = sections(project_type).select { |section| section["phase"] == phase.to_s }
      required = sections.flat_map { |section| section.fetch("fields", []).select { |field| field["required"] }.map { |field| field["id"] } }
      values = hash_value(fields)
      done = required.count { |field_id| values[field_id].present? }
      { "done" => done, "total" => required.length, "percent" => required.empty? ? 100 : (done.to_f / required.length * 100).round }
    end

    def review_summary(project_type, checks, phase)
      source = hash_value(checks)
      groups = sections(project_type).filter_map do |section|
        next unless section["phase"] == phase.to_s && section.fetch("checks", []).any?

        items = section["checks"].map { |key, label| { "key" => key, "label" => label, "done" => source[key] == true } }
        {
          "title" => section["title"],
          "items" => items,
          "done" => items.count { |item| item["done"] },
          "total" => items.length
        }
      end
      done = groups.sum { |group| group["done"] }
      total = groups.sum { |group| group["total"] }
      { "groups" => groups, "done" => done, "total" => total, "percent" => total.zero? ? 100 : (done.to_f / total * 100).round }
    end

    private

    def hash_value(value)
      value.respond_to?(:to_h) ? value.to_h.stringify_keys : {}
    end

    def rows(value)
      return value if value.is_a?(Array)
      return value.values if value.is_a?(Hash)

      []
    end

    def bounded(value, limit)
      value.to_s.strip[0, limit]
    end

    def normalize_date(value)
      return "" unless value.match?(/\A\d{4}-\d{2}-\d{2}\z/)

      Date.iso8601(value).iso8601
    rescue Date::Error
      ""
    end

    def truthy?(value)
      value == true || value.to_s == "1" || value.to_s.casecmp("true").zero?
    end
  end
end
