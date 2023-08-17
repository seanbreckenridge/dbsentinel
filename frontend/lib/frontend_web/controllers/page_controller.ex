defmodule FrontendWeb.PageController do
  use FrontendWeb, :controller

  def home(conn, _params) do
    # request the statistics from the data genserver
    statistics = GenServer.call(Frontend.DataServerState, :get_statistics)
    # assigns page title
    assign(conn, :page_title, "Summary")
    |> render(:home, statistics: statistics)
  end

  def search(conn, _params) do

  end
end
