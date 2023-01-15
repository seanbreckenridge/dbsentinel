import { z } from "zod";

import requestBackendEnv from "../../dataBackend";
import { createTRPCRouter, publicProcedure } from "../trpc";

export const SummaryValidator = z.object({
  status: z.string(),
  count: z.number(),
});

export type Summary = z.infer<typeof SummaryValidator>;

export const SummaryResponseValidator = z.object({
  anime: z.array(SummaryValidator),
  manga: z.array(SummaryValidator),
});

export type SummaryResponse = z.infer<typeof SummaryResponseValidator>;

export const dataRouter = createTRPCRouter({
  summary: publicProcedure
    .input(z.object({}).optional())
    .output(SummaryResponseValidator)
    .query(async () => requestBackendEnv<SummaryResponse>({ url: "summary/" })),
});
