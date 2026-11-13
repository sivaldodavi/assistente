Rails.application.routes.draw do
  get "up" => "rails/health#show", as: :rails_health_check
  root "public_pages#home"
  get "/login", to: "sessions#new", as: :login
  delete "/logout", to: "sessions#destroy", as: :logout
  get "/auth/google_oauth2/callback", to: "omniauth_callbacks#google_oauth2"
  get "/auth/failure", to: "omniauth_callbacks#failure"
  if Rails.env.development? || Rails.env.test?
    post "/auth/dev-login", to: "sessions#dev_login", as: :dev_login
  end
  get "/library", to: "sources#index", as: :library
  resources :sources, path: "library/sources", only: %i[create edit update destroy], controller: :sources
  post "/library/sources/:id/delete", to: "sources#delete", as: :delete_source
  get "/account/settings", to: "account_settings#show", as: :account_settings
  post "/account/settings/profile", to: "account_settings#update_profile", as: :account_update_profile
  post "/account/settings/terms", to: "account_settings#accept_terms", as: :account_accept_terms
  post "/account/settings/delete", to: "account_settings#delete_account", as: :account_delete
  get "/admin", to: "admin#index", as: :admin
  get "/admin/dashboard", to: "admin#dashboard", as: :admin_dashboard
  get "/admin/accounts", to: "admin#accounts", as: :admin_accounts
  patch "/admin/accounts/:id/plan", to: "admin#update_plan", as: :admin_account_plan
  patch "/admin/accounts/:id/credits", to: "admin#update_credits", as: :admin_account_credits
  patch "/admin/accounts/:id/block", to: "admin#update_block", as: :admin_account_block
  get "/admin/audit", to: "admin#audit", as: :admin_audit
  get "/admin/usage", to: "admin#usage", as: :admin_usage
  get "/admin/health", to: "admin#health", as: :admin_health
  get "/plans", to: "payments#plans", as: :plans
  get "/planos", to: "payments#plans", as: :pricing
  get "/termos", to: "public_pages#terms", as: :terms
  get "/privacidade", to: "public_pages#privacy", as: :privacy
  get "/ajuda-ia", to: "public_pages#ai_help", as: :ai_help
  get "/guia-de-escrita", to: "writing_guide#show", as: :writing_guide
  post "/guia-de-escrita/perguntas", to: "writing_guide#ask", as: :writing_guide_questions
  post "/payments", to: "payments#create", as: :payments
  get "/payments/:id", to: "payments#status", as: :payment_status
  post "/webhooks/mercadopago", to: "mercado_pago_webhooks#create", as: :mercadopago_webhook
  post "/projects/:project_id/ai/action", to: "project_assist#action"
  post "/projects/:project_id/ai/jev-report", to: "project_assist#jev_report"
  post "/projects/:project_id/ai/jev-section", to: "project_assist#jev_section"
  resources :projects do
    get :export, on: :member
    patch :paper_mode, on: :member
  end
end
