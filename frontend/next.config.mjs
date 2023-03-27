// @ts-check
/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation.
 * This is especially useful for Docker builds.
 */
!process.env.SKIP_ENV_VALIDATION && (await import("./src/env/server.mjs"));

/** @type {import("next").NextConfig} */
const config = {
  basePath: process.env.DBSENTINEL_BASE_PATH ?? undefined,
  reactStrictMode: true,
  swcMinify: true,
  i18n: {
    locales: ["en"],
    defaultLocale: "en",
  },
  images: {
    domains: [
      "api-cdn.myanimelist.net",
      "dbsentinel.s3.us-west-1.amazonaws.com",
    ],
    unoptimized: true,
    loader: "custom",
  },
};
export default config;
