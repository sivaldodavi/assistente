Rails.application.config.session_store :cookie_store,
  key: "_assistente_academico_session",
  same_site: Rails.env.production? ? :none : :lax,
  secure: Rails.env.production?
