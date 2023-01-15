import axios, { type AxiosResponse } from "axios";

export type RequestBackendProps = {
  url: string;
  backendUrl: string;
  auth: string;
  method?: string;
  body?: any;
  headers?: any;
};

async function requestBackend<T>({
  url,
  backendUrl,
  auth,
  method,
  body,
  headers,
}: RequestBackendProps): Promise<T> {
  const useUrl = `${backendUrl}/${url}`;
  const useMethod = method || "GET";
  const useBody = body ? JSON.stringify(body) : undefined;
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const headersWithAuth = {
    "Content-Type": "application/json",
    Authorization: auth,
    ...(headers ?? {}),
  };
  // dont really want to use axios, but cant figure out fetch with trpc
  // eslint-disable-next-line
  const resp: AxiosResponse = await axios.request<T>({
    url: useUrl,
    method: useMethod,
    data: useBody,
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    headers: headersWithAuth,
  });

  if (resp.status !== 200) {
    throw new Error(`requestBackend failed: ${resp.status}`);
  }
  return resp.data as T;
}

export default requestBackend;
