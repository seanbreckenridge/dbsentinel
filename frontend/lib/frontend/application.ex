defmodule Frontend.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Start the Telemetry supervisor
      FrontendWeb.Telemetry,
      # Start the Ecto repository
      Frontend.Repo,
      # Start the PubSub system
      {Phoenix.PubSub, name: Frontend.PubSub},
      # Start Finch
      {Finch, name: Frontend.Finch},
      # Start the Endpoint (http/https)
      FrontendWeb.Endpoint,
      # statistics/when data was last processed
      {Frontend.DataServerState, name: Frontend.DataServerState},
      # Start a worker by calling: Frontend.Worker.start_link(arg)
      # {Frontend.Worker, arg}
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: Frontend.Supervisor]
    Supervisor.start_link(children, opts)
  end

  # Tell Phoenix to update the endpoint configuration
  # whenever the application is updated.
  @impl true
  def config_change(changed, _new, removed) do
    FrontendWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
