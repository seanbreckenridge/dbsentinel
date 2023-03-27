import { env } from "../env/server.mjs";
import requestBackend from "../utils/backend";

export default function requestBackendEnv<T>({
  url,
  method,
  body,
  headers,
}: {
  url: string;
  method?: string;
  body?: unknown;
  headers?: unknown;
}) {
  console.log(env.DATA_BACKEND_URL)
  return requestBackend<T>({
    url,
    method,
    body,
    headers,
    backendUrl: env.DATA_BACKEND_URL,
    auth: env.DATA_BACKEND_SECRET,
  });
}
