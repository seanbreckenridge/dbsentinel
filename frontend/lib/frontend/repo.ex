defmodule Frontend.Repo do
  use Ecto.Repo,
    otp_app: :frontend,
    adapter: Ecto.Adapters.SQLite3
end
