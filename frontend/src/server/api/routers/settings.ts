import { z } from "zod";

import { createTRPCRouter, protectedProcedure } from "../trpc";

export const settingsRouter = createTRPCRouter({
  updateSettings: protectedProcedure
    .input(
      z.object({
        name: z.string().optional(),
        username: z.string().min(4).max(30).optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const data = {
        ...(input.name ? { name: input.name } : {}),
        ...(input.username ? { username: input.username } : {}),
      };
      await ctx.prisma.user.update({
        where: {
          id: ctx.session.user.id,
        },
        data: data,
      });
    }),
});
