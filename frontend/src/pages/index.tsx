import { type NextPage } from "next";
import Head from "next/head";
import { signIn, signOut, useSession } from "next-auth/react";
import { type Summary } from "../server/api/routers/data";

import { api } from "../utils/api";

const Home: NextPage = () => {
  const summary = api.data.summary.useQuery();

  return (
    <>
      <Head>
        <title>Malsentinel</title>
        <meta name="description" content="malsentinel " />
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
              <div className="container mx-auto w-full">
                  <div className="text-2xl">
                    Global Stats
                  </div>
                <div className="flex w-full flex-col justify-center sm:flex-row items-center">
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
                            <div className="mr-6">{item.status}</div>
                            <div>{item.count}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
};

export default Home;

const AuthShowcase: React.FC = () => {
  const { data: sessionData } = useSession();

  const { data: secretMessage } = api.example.getSecretMessage.useQuery(
    undefined, // no input
    { enabled: sessionData?.user !== undefined }
  );

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <p className="text-center text-2xl text-white">
        {sessionData && <span>Logged in as {sessionData.user?.name}</span>}
        {secretMessage && <span> - {secretMessage}</span>}
      </p>
      <button
        className="rounded-full bg-white/10 px-10 py-3 font-semibold text-white no-underline transition hover:bg-white/20"
        onClick={sessionData ? () => void signOut() : () => void signIn()}
      >
        {sessionData ? "Sign out" : "Sign in"}
      </button>
    </div>
  );
};
