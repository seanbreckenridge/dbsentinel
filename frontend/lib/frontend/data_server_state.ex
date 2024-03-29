defmodule Frontend.DataServerState do
  @moduledoc """
  A genserver that keeps track of the state of the data serverupdate_st
  """
  use GenServer
  require Logger

  @data_server_url Application.compile_env(:frontend, :data_server_url, "http://localhost:5200")

  def start_link(_) do
    GenServer.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  def init(:ok) do
    state = %{
      statistics: %{},
      called_update_metadata: nil,
      called_full_db_update: nil
    }

    # start state update loops
    Process.send_after(self(), :update_statistics_loop, 0)
    Process.send_after(self(), :update_evry_files_loop, 0)

    {:ok, state}
  end

  def handle_info(:update_statistics_loop, state) do
    Process.send_after(self(), :update_statistics, 1000)
    # reschedule to run once an hour
    Process.send_after(self(), :update_statistics_loop, 60 * 60 * 1000)
    {:noreply, state}
  end

  def handle_info(:update_evry_files_loop, state) do
    Process.send_after(self(), :update_evry_files, 1000)
    # reschedule to run once every 10 minutes
    Process.send_after(self(), :update_evry_files_loop, 10 * 60 * 1000)
    {:noreply, state}
  end

  # call self to request statistics once an hour
  def handle_info(:update_statistics, state) do
    case request_statistics() do
      {:ok, statistics} ->
        Logger.info("Updated statistics")
        # convert keys to atoms
        statistics =
          Enum.map(statistics, fn {k, v} ->
            {String.to_atom(k), v |> Enum.map(&map_keys_to_atoms/1)}
          end)

        {:noreply, Map.put(state, :statistics, statistics)}

      {:error, err} ->
        Logger.error("Could not update statistics: #{inspect(err)}")
        {:noreply, state}
    end
  end

  def handle_info(:update_evry_files, state) do
    {:noreply, parse_evry_files(state)}
  end

  def handle_call(:get_statistics, _from, state) do
    cond do
      state.statistics == %{} ->
        # try to update
        send(self(), :update_statistics)
        {:reply, {:error, "No statistics available"}, state}

      true ->
        {:reply, {:ok, state.statistics}, state}
    end
  end

  defp map_keys_to_atoms(map) do
    map |> Enum.map(fn {k, v} -> {String.to_atom(k), v} end) |> Map.new()
  end

  defp request_statistics() do
    case Tesla.get(@data_server_url <> "/summary/") do
      {:ok, %{body: body}} ->
        # parse as JSON
        case Jason.decode(body) do
          {:ok, statistics} ->
            {:ok, statistics}

          {:error, _} ->
            {:error, "Could not parse statistics as JSON"}
        end

      {:error, _} ->
        {:error, "Could not get statistics, data server is probably down/unresponsive"}
    end
  end

  defp parse_evry_files(state) when is_map(state) do
    state = Map.put(state, :called_update_metadata, parse_evry_file!("update-metadata"))
    state = Map.put(state, :called_full_db_update, parse_evry_file!("dbsentinel-full-db-update"))

    Logger.info(
      "evry: #{inspect(Map.take(state, [:called_update_metadata, :called_full_db_update]))}"
    )

    state
  end

  defp parse_evry_file!(name) do
    {_, value} = parse_evry_file(name)
    value
  end

  @evry_data_dir System.get_env("EVRY_DATA_DIR") ||
                   System.user_home() <> "/.local/share/evry/data"

  @doc """
  parse the file in ~/.local/share/evry/data/
  that has a datetime like 1692238337154 in milliseconds
  """
  def parse_evry_file(name) when is_binary(name) do
    case File.read(@evry_data_dir <> "/" <> name) do
      {:ok, content} ->
        ms = content |> String.trim() |> String.to_integer()
        {:ok, ms / 1000}

      {:error, _} ->
        {:error, nil}
    end
  end
end
