import { z } from "zod";

import requestBackendEnv from "../../dataBackend";
import { createTRPCRouter, publicProcedure } from "../trpc";

import { allMediaTypesZod } from "./mediaTypes";

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

const QueryInputValidator = z.object({
  title: z.string().optional(),
  entry_type: z.enum(["anime", "manga"]).optional(),
  media_type: allMediaTypesZod.optional(),
  member_count: z.number().nullish(),
  average_episode_duration: z.number().nullish(),
  nsfw: z.boolean().optional(),
  json_data: z.object({}).optional(),
  approved_status: z.enum([
    "approved",
    "denied",
    "unapproved",
    "deleted",
    "all",
  ]),
  offset: z.number().default(0),
  limit: z.number(),
  order_by: z
    .enum([
      "id",
      "title",
      "start_date",
      "end_date",
      "status_updated_at",
      "metadata_updated_at",
      "member_count",
      "average_episode_duration",
    ])
    .default("id"),
  sort: z.enum(["asc", "desc"]).default("desc"),
});

export type QueryInput = z.infer<typeof QueryInputValidator>;

const QueryOuputEntryValidator = z.object({
  id: z.number(),
  title: z.string(),
  nsfw: z.boolean().nullish(),
  alternate_titles: z.any(),
  image_url: z.string().nullish(),
  media_type: allMediaTypesZod.nullish(),
  json_data: z.any(),
  approved_status: z.enum(["approved", "denied", "unapproved", "deleted"]),
  start_date: z.string().nullish(),
  end_date: z.string().nullish(),
  member_count: z.number().nullish(),
  average_episode_duration: z.number().nullish(),
  metadata_updated_at: z.number(),
  status_updated_at: z.number(),
});

const QueryOutputValidator = z.object({
  entry_type: z.enum(["anime", "manga"]),
  total_count: z.number(),
  results: z.array(QueryOuputEntryValidator),
});

export type QueryOutput = z.infer<typeof QueryOutputValidator>;

export const dataRouter = createTRPCRouter({
  summary: publicProcedure
    .output(SummaryResponseValidator)
    .query(async () => requestBackendEnv<SummaryResponse>({ url: "summary/" })),
  dataQuery: publicProcedure
    .input(QueryInputValidator)
    .output(QueryOutputValidator)
    .query(async ({ input }) => {
      return await requestBackendEnv<QueryOutput>({
        url: "query/",
        method: "POST",
        body: input,
      });
    }),
});
