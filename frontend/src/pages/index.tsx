import { type NextPage } from "next";
import Head from "next/head";
import Link from "next/link";
import { type Summary } from "../server/api/routers/data";

import { api } from "../utils/api";
import { ssg } from "../utils/ssg";

const Home: NextPage = () => {
  const summary = api.data.summary.useQuery(undefined, {
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  });

  return (
    <>
      <Head>
        <title>DBsentinel</title>
        <meta
          name="description"
          content="search deleted/denied MAL info, connections to other databases"
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main>
        <section className="flex w-full flex-col items-center px-4 text-center">
          <div className="flex w-full flex-col items-center justify-center pt-2 sm:flex-row">
            <Link
              className="m-2 text-blue-600 transition-colors duration-200 hover:text-blue-700"
              href="/search?entry_type=anime&status=approved&order_by=status_updated_at&sort=desc"
            >
              Recently Approved Anime
            </Link>
          </div>
          <div className="flex w-full flex-col items-center justify-center sm:flex-row">
            <Link
              className="m-2 text-blue-600 transition-colors duration-200 hover:text-blue-700"
              href="/search?entry_type=anime&status=unapproved&order_by=id&sort=desc"
            >
              Recently Submitted Unapproved Anime
            </Link>
          </div>
        </section>
        <hr className="mx-auto my-2 w-6/12 border-gray-300" />
        <section
          className="flex w-full flex-col  items-center px-4 text-center"
          id="summary"
        >
          <div className="flex w-full flex-col items-center">
            {summary.error ? (
              <div className="text-2xl">Error: {summary.error.message}</div>
            ) : !summary.data ? (
              <div className="text-2xl">Loading...</div>
            ) : (
              <div className="container mx-auto flex w-full flex-col justify-center">
                <div className="text-2xl">Global Stats</div>
                <div className="flex w-full flex-col items-center justify-center sm:flex-row">
                  {Object.keys(summary.data).map((key) => (
                    <div key={key}>
                      <div className="m-2 flex flex-col items-center rounded-md border-2 border-gray-300 p-5">
                        <div className="mb-2 text-2xl">{key}</div>
                        {(key == "anime"
                          ? summary.data.anime
                          : summary.data.manga
                        ).map((item: Summary) => (
                          <div
                            className="flex w-full flex-row justify-between"
                            key={item.status}
                          >
                            <div
                              className="mr-6"
                              title={`Search ${item.status} ${key} data`}
                            >
                              <Link
                                className="text-blue-500 transition-colors duration-200 hover:text-blue-700"
                                href={`/search/?entry_type=${key}&status=${item.status}`}
                              >
                                {item.status}
                              </Link>
                            </div>
                            <div>{item.count}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="text-xs text-gray-500">
                  <div className="text-center">
                    Click on a status to search data
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
};

export async function getStaticProps() {
  await ssg.data.summary.prefetch(undefined);
  return {
    props: {
      trpcState: ssg.dehydrate(),
    },
    revalidate: 1,
  };
}

export default Home;
