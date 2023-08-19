defmodule Frontend.DataServer do
  use Tesla
  adapter({Tesla.Adapter.Hackney, recv_timeout: 10_000})

  @url Application.compile_env(:frontend, :data_server_url)

  plug(Tesla.Middleware.Logger)
  plug(Tesla.Middleware.BaseUrl, @url)

  plug(Tesla.Middleware.Headers, [
    {"content-type", "application/json"}
  ])

  plug(Tesla.Middleware.JSON)

  plug(Tesla.Middleware.Retry,
    max_retries: 3,
    delay: 500,
    retry_interval: 500,
    max_delay: 5000,
    retry_statuses: [500]
  )

  defp page(n) when is_nil(n), do: page(1)
  defp page(n) when is_binary(n), do: page(String.to_integer(n))
  defp page(n) when n <= 0, do: page(1)

  defp page(n) when n > 0 do
    %{
      limit: 100,
      offset: (n - 1) * 100
    }
  end

  defp parse_media_type(nil), do: nil
  defp parse_media_type("all"), do: nil
  defp parse_media_type(s) when is_binary(s), do: s

  defp average_episode_duration(nil), do: "-"
  defp average_episode_duration(0), do: "-"
  defp average_episode_duration(s) when is_float(s), do: average_episode_duration(round(s))

  defp average_episode_duration(n) when is_integer(n) do
    count = n |> Kernel./(60) |> round()

    case count do
      0 -> "-"
      _ -> "#{count} min"
    end
  end

  defp episode_volume_chapter(nil), do: "-"
  defp episode_volume_chapter(0), do: "-"
  defp episode_volume_chapter(s) when is_integer(s), do: s

  defp strip_string(nil), do: nil
  defp strip_string(""), do: nil

  defp strip_string(s) when is_binary(s) do
    case s |> String.trim() do
      "" -> nil
      s -> s
    end
  end

  def unslugify(nil), do: nil
  def unslugify(""), do: nil

  def unslugify(s) do
    s |> String.replace("_", " ")
  end

  @allowed_json_keys ["num_episodes", "volumes", "chapters"] |> MapSet.new()

  @base_url Application.compile_env(:frontend, :base_url, "")

  def parse_search_result_item(item, entry_type) do
    item
    |> Map.put("url", "https://myanimelist.net/#{entry_type}/#{item["id"]}")
    |> Map.put(
      "media_type",
      unslugify(item["media_type"]) || "unknown"
    )
    |> Map.put("member_count", item["member_count"] || "-")
    |> Map.put(
      "average_episode_duration",
      average_episode_duration(item["average_episode_duration"])
    )
    # link to the entry pageon the frontend
    |> Map.put(
      "entry_url",
      "#{@base_url}/#{entry_type}/#{item["id"]}"
    )
    |> Map.put(
      "json_map",
      item["json_data"]
      |> Map.to_list()
      |> Enum.filter(fn {k, _} -> MapSet.member?(@allowed_json_keys, k) end)
      |> Enum.map(fn {k, v} -> {unslugify(k), episode_volume_chapter(v)} end)
      # rename num_episodes to episodes
      |> Enum.map(fn {k, v} ->
        case k do
          "num episodes" -> {"episodes", v}
          _ -> {k, v}
        end
      end)
      |> Enum.into(%{})
    )
  end

  def parse_search_response(nil),
    do: %{
      results: [],
      entry_type: nil,
      total_count: 0
    }

  def parse_search_response(response) when is_map(response) do
    items =
      response["results"]
      |> Enum.map(fn item -> parse_search_result_item(item, response["entry_type"]) end)

    %{
      results: items,
      entry_type: response["entry_type"],
      total_count: response["total_count"]
    }
  end

  defp parse_params(params) do
    {sfw, params} = Map.pop(params, "sfw")
    {nsfw, params} = Map.pop(params, "nsfw")

    nsfw_param =
      cond do
        is_nil(sfw) && is_nil(nsfw) -> nil
        is_nil(sfw) && nsfw == "on" -> true
        is_nil(sfw) && nsfw == "off" -> false
        sfw == "on" && is_nil(nsfw) -> false
        sfw == "off" && is_nil(nsfw) -> true
        true -> false
      end

    Map.merge(
      %{
        title: strip_string(params["title"]),
        entry_type: params["entry_type"] || "anime",
        media_type: parse_media_type(params["media_type"]),
        nsfw: nsfw_param,
        json_data: params["json_data"],
        approved_status: params["status"] || "all",
        order_by: params["order_by"] || "id",
        sort: params["sort"] || "desc"
      },
      page(params["page"])
    )
  end

  def search(params) do
    post("/query/", parse_params(params))
  end

  def by_id(id, type) do
    case post("/query/id/", %{
           id: id,
           entry_type: type
         }) do
      {:ok, response} ->
        case response.status do
          200 -> {:ok, response.body}
          404 -> {:error, :not_found}
          _ -> {:error, :unknown}
        end

      {:error, _} ->
        {:error, nil}
    end
  end
end

defmodule FrontendWeb.PageController do
  use FrontendWeb, :controller

  def home(conn, _params) do
    # request the statistics from the data genserver
    {statistics, conn} =
      case GenServer.call(Frontend.DataServerState, :get_statistics) do
        {:ok, statistics} -> {statistics, conn}
        # Note: when this fails, it tries to update the statistics
        {:error, _} -> {%{}, conn |> put_flash(:error, "Failed to get statistics")}
      end

    # assigns page title 
    assign(conn, :page_title, "Summary")
    |> render(:home, statistics: statistics)
  end

  def search(conn, params) do
    # request the search results from the data server
    {response_body, conn} =
      case Frontend.DataServer.search(params) do
        {:ok, response} ->
          case response.status do
            200 ->
              {response.body, conn}

            _ ->
              {nil,
               conn |> put_flash(:error, "Failed to get search results. Please try again later")}
          end

        {:error, _} ->
          {nil, conn |> put_flash(:error, "Failed to get search results. Please try again later")}
      end

    assign(conn, :page_title, "Search")
    |> render(:search,
      params: params,
      data: Frontend.DataServer.parse_search_response(response_body)
    )
  end

  def by_id_anime(conn, %{"id" => id}) do
    by_id(conn, %{"id" => id, "type" => "anime"})
  end

  def by_id_manga(conn, %{"id" => id}) do
    by_id(conn, %{"id" => id, "type" => "manga"})
  end

  def by_id(conn, %{"id" => id, "type" => type}) do
    {type, conn} =
      case type do
        "anime" -> {"anime", conn}
        "manga" -> {"manga", conn}
        type -> {type, conn |> put_flash(:error, "Invalid type #{type}") |> redirect(to: "/")}
      end

    case Frontend.DataServer.by_id(id, type) do
      {:ok, result} ->
        assign(conn, :page_title, "#{type} #{id}")
        |> render(:by_id, data: Jason.encode!(result, pretty: true))

      {:error, _} ->
        conn
        |> put_flash(:error, "Failed to get #{type} with id #{id}")
        |> redirect(to: "/")
    end
  end
end
