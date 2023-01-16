import { type NextPage } from "next";
import Head from "next/head";
import Link from "next/link";
import { type Summary } from "../server/api/routers/data";

import { api } from "../utils/api";

const Home: NextPage = () => {
  const summary = api.data.summary.useQuery();

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
                                href={`/search/?media_type=${key}&status=${item.status}`}
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
                <caption className="text-xs text-gray-500">
                  <div className="text-center">
                    Click on a status to search data
                  </div>
                </caption>
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
};

export default Home;
