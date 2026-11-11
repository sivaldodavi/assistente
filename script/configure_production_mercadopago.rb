require "json"
require "open3"
require "shellwords"

module ProductionMercadoPagoSetup
  SERVER = "root@159.223.136.31"
  SECRET_DIRECTORY = "/opt/servidor/secrets/assistente-academico-production"

  REMOTE_INSTALLER = <<~'PYTHON'
    import json
    import os
    import stat
    import sys

    directory = "/opt/servidor/secrets/assistente-academico-production"
    info = os.stat(directory, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit("production secrets directory has unexpected owner or permissions")

    required = {"rails.env", "deepseek_api_key", "typesafe_api_key"}
    existing = {entry.name for entry in os.scandir(directory)}
    if not required.issubset(existing):
        raise SystemExit("existing production secrets are incomplete")

    expected_permissions = {
        "rails.env": (0, 0, 0o600),
        "deepseek_api_key": (1000, 1000, 0o400),
        "typesafe_api_key": (1000, 1000, 0o400),
    }
    for name, (uid, gid, mode) in expected_permissions.items():
        path = os.path.join(directory, name)
        item = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISREG(item.st_mode)
            or item.st_uid != uid
            or item.st_gid != gid
            or stat.S_IMODE(item.st_mode) != mode
        ):
            raise SystemExit("an existing production secret has unexpected owner or permissions")

    names = {
        "mercadopago_access_token": "mercadopago_access_token",
        "mercadopago_webhook_secret": "mercadopago_webhook_secret",
    }
    if any(os.path.lexists(os.path.join(directory, name)) for name in names.values()):
        raise SystemExit("production Mercado Pago files already exist; refusing to overwrite")

    values = json.load(sys.stdin)
    if set(values) != set(names) or any(
        not isinstance(value, str)
        or not value
        or len(value.encode()) > 4096
        or any(character in value for character in "\r\n\0")
        for value in values.values()
    ):
        raise SystemExit("invalid production Mercado Pago values")

    created = []
    try:
        for field, name in names.items():
            path = os.path.join(directory, name)
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            created.append(path)
            os.fchown(descriptor, 1000, 1000)
            os.fchmod(descriptor, 0o400)
            with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
                secret_file.write(values[field] + "\n")
                secret_file.flush()
                os.fsync(secret_file.fileno())
    except BaseException:
        for path in created:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        raise

    print("Production Mercado Pago files installed for app UID 1000 with mode 0400.")
  PYTHON

  def self.run(input: $stdin, output: $stdout, transfer: nil)
    output.puts "Este assistente grava somente os segredos de PRODUÇÃO do Mercado Pago no VPS."
    output.puts "As credenciais sandbox de staging não serão lidas, alteradas nem removidas."
    output.puts "Os valores digitados e a conferência ficarão visíveis neste terminal."
    output.puts "Não cole credenciais no chat."
    output.puts "A URL de webhook da aplicação é https://trab.sivaldodavi.com.br/webhooks/mercadopago."
    output.puts "Não envie um teste de webhook ainda; a rota pública continua apontando para staging."
    output.puts

    access_token = read_value(input, output, "Access Token de produção")
    webhook_secret = read_value(input, output, "Segredo de assinatura do webhook de produção")
    validate!(access_token, "Access Token")
    validate!(webhook_secret, "Segredo de assinatura")

    output.puts
    output.puts "Confirme no painel do Mercado Pago que o seletor estava em PRODUÇÃO."
    output.print "Digite PRODUCAO para confirmar o ambiente: "
    return :cancelled unless input.gets&.chomp == "PRODUCAO"

    output.puts
    output.puts "Confira os valores que serão enviados apenas ao VPS:"
    output.puts "Access Token de produção: #{access_token}"
    output.puts "Segredo do webhook de produção: #{webhook_secret}"
    output.puts "Destino: #{SECRET_DIRECTORY}"
    output.print "Digite SIM para instalar; qualquer outra resposta cancela: "
    return :cancelled unless input.gets&.chomp == "SIM"

    (transfer || method(:transfer)).call(access_token:, webhook_secret:)
    output.puts "Segredos de produção instalados. O staging não foi alterado."
    :saved
  end

  def self.transfer(access_token:, webhook_secret:)
    remote_command = "python3 -c #{Shellwords.escape(REMOTE_INSTALLER)}"
    stdout, _stderr, status = Open3.capture3(
      "ssh",
      SERVER,
      remote_command,
      stdin_data: JSON.generate(
        mercadopago_access_token: access_token,
        mercadopago_webhook_secret: webhook_secret
      )
    )
    raise "Falha na instalação remota (ssh exit #{status.exitstatus})." unless status.success?

    $stdout.puts stdout
  end
  private_class_method :transfer

  def self.read_value(input, output, label)
    output.print "#{label}: "
    value = input.gets
    raise "Entrada encerrada antes de concluir." unless value

    value.chomp.strip
  end
  private_class_method :read_value

  def self.validate!(value, label)
    return if !value.empty? && value.bytesize <= 4_096 && !value.match?(/[\r\n\0]/)

    raise "#{label} vazio, inválido ou excede o limite de tamanho."
  end
  private_class_method :validate!
end

ProductionMercadoPagoSetup.run if $PROGRAM_NAME == __FILE__
