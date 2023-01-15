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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  headers?: any;
}) {
  return requestBackend<T>({
    url,
    method,
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    body,
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    headers,
    backendUrl: env.DATA_BACKEND_URL,
    auth: env.DATA_BACKEND_SECRET,
  });
}
