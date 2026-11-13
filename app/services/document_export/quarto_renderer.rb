require "fileutils"
require "tmpdir"
require "timeout"

class DocumentExport
  # Renderiza o Quarto/Typst em diretório temporário isolado, com limite de concorrência e tempo.
  class QuartoRenderer
    EXTENSION_DIR = Rails.root.join("vendor/quarto/_extensions/abnt")
    RENDER_TIMEOUT_SECONDS = 90
    MAX_PDF_BYTES = 25 * 1024 * 1024
    MAX_CONCURRENT_RENDERS = 2
    MUTEX = Mutex.new
    @active_renders = 0

    class << self
      def render(source)
        executable = executable_path
        raise DocumentExport::QuartoUnavailable, "O renderizador Quarto não está disponível." unless executable && EXTENSION_DIR.directory?
        raise DocumentExport::QuartoBusy, "Há muitas renderizações em andamento." unless acquire_slot

        begin
          render_isolated(source, executable)
        ensure
          release_slot
        end
      end

      private

      def executable_path
        binary = ENV.fetch("QUARTO_BINARY", "quarto")
        return binary if binary.include?(File::SEPARATOR) && File.executable?(binary)

        ENV.fetch("PATH", "/usr/local/bin:/usr/bin:/bin").split(File::PATH_SEPARATOR).each do |directory|
          candidate = File.join(directory, binary)
          return candidate if File.executable?(candidate)
        end
        nil
      end

      def acquire_slot
        MUTEX.synchronize do
          return false if @active_renders >= MAX_CONCURRENT_RENDERS

          @active_renders += 1
        end
        true
      end

      def release_slot
        MUTEX.synchronize { @active_renders -= 1 }
      end

      def render_isolated(source, executable)
        Dir.mktmpdir("assistente-quarto-") do |workspace|
          extensions = File.join(workspace, "_extensions")
          FileUtils.mkdir_p(extensions)
          FileUtils.cp_r(EXTENSION_DIR, File.join(extensions, "abnt"))
          source_path = File.join(workspace, "document.qmd")
          output_path = File.join(workspace, "document.pdf")
          File.write(source_path, source, mode: "w:UTF-8")
          home = File.join(workspace, "home")
          FileUtils.mkdir_p(home, mode: 0o700)
          environment = {
            "PATH" => ENV.fetch("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME" => home,
            "TMPDIR" => workspace,
            "TMP" => workspace,
            "TEMP" => workspace,
            "LANG" => ENV.fetch("LANG", "C.UTF-8"),
            "LC_ALL" => ENV.fetch("LC_ALL", "C.UTF-8")
          }
          pid = Process.spawn(
            environment,
            executable,
            "render",
            File.basename(source_path),
            "--output",
            File.basename(output_path),
            chdir: workspace,
            in: File::NULL,
            out: File::NULL,
            err: File::NULL,
            pgroup: true,
            unsetenv_others: true
          )
          status = wait_for_renderer(pid)
          unless status.success? && File.file?(output_path)
            raise QuartoRenderError, "O Quarto não conseguiu renderizar este documento."
          end
          raise QuartoRenderError, "O PDF gerado excedeu o limite de tamanho." if File.size(output_path) > MAX_PDF_BYTES

          pdf = File.binread(output_path)
          raise QuartoRenderError, "O renderizador não retornou um PDF válido." unless pdf.start_with?("%PDF-")

          pdf
        rescue Errno::ENOENT
          raise QuartoUnavailable, "Não foi possível iniciar o Quarto."
        end
      end

      def wait_for_renderer(pid)
        Timeout.timeout(RENDER_TIMEOUT_SECONDS) do
          _pid, status = Process.wait2(pid)
          status
        end
      rescue Timeout::Error
        terminate_renderer(pid)
        raise QuartoRenderError, "A renderização excedeu o tempo limite."
      end

      def terminate_renderer(pid)
        Process.kill("TERM", -pid)
        sleep 0.25
        Process.kill("KILL", -pid)
      rescue Errno::ESRCH
        nil
      ensure
        begin
          Process.waitpid(pid)
        rescue Errno::ECHILD
          nil
        end
      end
    end
  end
end
