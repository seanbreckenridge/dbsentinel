import axios, { type AxiosResponse } from "axios";

export type RequestBackendProps = {
  url: string;
  backendUrl: string;
  auth: string;
  method?: string;
  body?: unknown;
  headers?: unknown;
};

async function requestBackend<T>({
  url,
  backendUrl,
  auth,
  method,
  body,
  headers,
}: RequestBackendProps): Promise<T> {
  const headersWithAuth = {
    "Content-Type": "application/json",
    Authorization: auth,
    ...(headers ?? {}),
  };
  // dont really want to use axios, but cant figure out fetch with trpc
  const resp: AxiosResponse = await axios.request<T>({
    url: `${backendUrl}/${url}`,
    method: method || "GET",
    data: body ?? {},
    headers: headersWithAuth,
  });

  // console.log(resp.data);

  if (resp.status >= 400) {
    throw new Error(`requestBackend failed: ${resp.status}`);
  }
  return resp.data as T;
}

export default requestBackend;
