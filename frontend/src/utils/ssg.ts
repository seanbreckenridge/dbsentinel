import { createProxySSGHelpers } from "@trpc/react-query/ssg";
import { appRouter } from "../server/api/root";
import { prisma } from "../server/db";
import superjson from "superjson";

// https://trpc.io/docs/ssg
export const ssg = createProxySSGHelpers({
  router: appRouter,
  ctx: { session: null, prisma },
  transformer: superjson,
});
