class SourcesController < ApplicationController
  SOURCE_KIND_LABELS = {
    "book" => "Livro",
    "article" => "Artigo",
    "legislation" => "Legislação",
    "case_law" => "Jurisprudência",
    "website" => "Site",
    "other" => "Outro"
  }.freeze

  before_action :authenticate_account!
  before_action :set_source, only: %i[edit update destroy delete]

  def index
    @sources = current_account.sources.order(updated_at: :desc, title: :asc)
    @source = Source.new
  end

  def create
    @source = current_account.sources.new(source_params)
    if @source.save
      redirect_to library_path(saved: "source"), notice: "Fonte adicionada à Biblioteca Pessoal."
    else
      prepare_library
      render :index, status: :unprocessable_entity
    end
  end

  def edit
    prepare_library
    render :index
  end

  def update
    if @source.update(source_params)
      redirect_to library_path(saved: "source-updated"), notice: "Fonte atualizada."
    else
      prepare_library
      render :index, status: :unprocessable_entity
    end
  end

  def destroy
    @source.destroy!
    head :no_content
  end

  def delete
    @source.destroy!
    redirect_to library_path(saved: "source-deleted"), notice: "Fonte removida."
  end

  private

  def set_source
    @source = current_account.sources.find(params[:id])
  end

  def source_params
    params.require(:source).permit(:title, :author, :kind, :reference, :notes)
  end

  def prepare_library
    @sources = current_account.sources.order(updated_at: :desc, title: :asc)
    @editing_id = @source.persisted? ? @source.id : nil
  end
end
