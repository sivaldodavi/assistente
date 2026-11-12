class AcademicSchedule
  class << self
    def normalize_schedule(raw)
      tasks = rows(hash_value(raw)["tasks"]).first(100).filter_map do |item|
        values = hash_value(item)
        raw_date = values["date"]
        due_date = normalize_date(raw_date)
        next if raw_date.present? && due_date.blank?

        title = bounded(values["title"], 180)
        next if title.blank? && due_date.blank? && values["id"].blank?

        {
          "id" => bounded(values["id"].presence || SecureRandom.uuid, 80),
          "title" => title,
          "date" => due_date,
          "done" => truthy?(values["done"])
        }
      end

      { "tasks" => tasks }
    end

    def summary(schedule)
      tasks = normalize_schedule(schedule)["tasks"]
      {
        "task_total" => tasks.length,
        "task_done" => tasks.count { |task| task["done"] }
      }
    end

    def upcoming(projects, today: Date.current)
      entries = Array(projects).flat_map do |project|
        if project.respond_to?(:schedule)
          task_entries(project.schedule, project_id: project.id.to_s, title: project.title)
        else
          attributes = hash_value(project)
          task_entries(attributes["schedule"], project_id: attributes["id"], title: attributes["title"])
        end
      end
      upcoming = entries.reject { |item| item["done"] || item["date"].blank? }.map do |item|
        item.merge("overdue" => item["date"] < today.iso8601)
      end.sort_by { |item| [ item["date"], item["title"], item["label"] ] }
      { "entries" => upcoming, "has_entries" => upcoming.any?, "today" => today.iso8601 }
    end

    private

    def task_entries(schedule, project_id:, title:)
      normalize_schedule(schedule)["tasks"].filter_map do |task|
        next if task["date"].blank?

        date = task["date"]
        {
          "project_id" => project_id.to_s,
          "title" => title.presence || "Trabalho sem título",
          "kind" => "task",
          "label" => task["title"].presence || "Tarefa sem título",
          "date" => date,
          "date_label" => Date.iso8601(date).strftime("%d/%m/%Y"),
          "task_id" => task["id"],
          "done" => task["done"]
        }
      end
    end

    def hash_value(value)
      return value.to_unsafe_h.stringify_keys if value.respond_to?(:to_unsafe_h)
      return value.stringify_keys if value.is_a?(Hash)

      {}
    end

    def rows(value)
      return value if value.is_a?(Array)
      return value.values if value.is_a?(Hash)

      []
    end

    def normalize_date(value)
      text = value.to_s.strip
      return "" if text.blank?

      text = "#{text[6, 4]}-#{text[3, 2]}-#{text[0, 2]}" if text.match?(/\A\d{2}\/\d{2}\/\d{4}\z/)
      Date.iso8601(text).iso8601
    rescue Date::Error
      ""
    end

    def bounded(value, limit)
      value.to_s.strip[0, limit]
    end

    def truthy?(value)
      value == true || value.to_s == "1" || value.to_s.casecmp("true").zero?
    end
  end
end
