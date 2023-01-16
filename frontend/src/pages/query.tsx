import { type NextPage } from "next";
import Head from "next/head";
import { useState, useRef, useEffect } from "react";
import ReactPaginate from "react-paginate";
import { type QueryOutput } from "../server/api/routers/data";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronLeft,
} from "@fortawesome/free-solid-svg-icons";

import { api } from "../utils/api";

const Query: NextPage = () => {
  // form values
  const [title, setTitle] = useState("");
  const [entryType, setEntryType] = useState("anime");
  const [sfw, setSfw] = useState(true);
  const [nsfw, setNsfw] = useState(false);
  const [approvedStatus, setApprovedStatus] = useState("approved");
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(100);
  const pageCount = useRef(1);

  const resetPagination = () => {
    setPage(0);
    pageCount.current = 1;
  };

  let nsfwQuery = undefined;
  if (sfw && !nsfw) {
    nsfwQuery = false;
  } else if (!sfw && nsfw) {
    nsfwQuery = true;
  }

  const query = api.data.dataQuery.useQuery(
    {
      entry_type:
        entryType === "anime" || entryType === "manga" ? entryType : undefined,
      title: title.length > 0 ? title : undefined,
      nsfw: nsfwQuery,
      approved_status:
        approvedStatus === "approved" ||
        approvedStatus === "denied" ||
        approvedStatus === "unapproved" ||
        approvedStatus === "deleted"
          ? approvedStatus
          : undefined,
      offset: page * limit,
      limit: limit,
    },
    {
      onSuccess: (data: QueryOutput) => {
        pageCount.current = Math.ceil(data.total_count / limit);
      },
    }
  );

  useEffect(() => {
    if (query.data) {
      pageCount.current = Math.ceil(query.data.total_count / limit);
    }
  }, [limit, query.data, query.data?.total_count]);

  return (
    <>
      <Head>
        <title>DBsentinel - Query</title>
        <meta name="description" content="query deleted/denied MAL info" />
        <link rel="icon" href="/favicon.ico" />
        <style>{`
          .item {
  align-items: center;
  color: #eee;
  display: flex;
  font-size: 1rem;
  height: 2rem;
  padding: 0 1rem;
  margin: 0 0.2rem;
  flex-grow: 0;
  justify-content: center;
  width: 2rem;
}

.active {
  border: solid 1px darkblue;
  border-radius: 40px;
  color: darkblue;
}


.next, .previous {
  flex-grow: 1;
  color: darkblue;
  padding: 0 2rem;
  max-width: 5rem;
}

.next:hover, .previous:hover {
  color: #eee;
  transition: 0.2s;
}

.pagination {
  align-items: center;
  background-color: #0fbcf9;
  display: flex;
  flex-direction: row;
  height: 60px;
  justify-content: center;
  list-style-type: none;
  position: relative;
  width: 100%;
}

.pagination-page {
  font-weight: 700;
}

          `}</style>
      </Head>
      <main className="container mx-auto flex min-h-screen flex-col items-center justify-start">
        <section className="flex w-full flex-col items-start justify-center border-2 border-black p-3">
          <form
            className="flex w-full flex-col items-start justify-center"
            onSubmit={(e) => e.preventDefault()}
          >
            <label htmlFor="title" className="m-1">
              Title
              <input
                className="ml-2 rounded-md border-2 border-gray-300 p-2"
                type="text"
                placeholder="Title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  resetPagination();
                }}
              />
            </label>
            <label htmlFor="entryType" className="m-1">
              Type
              <select
                className="ml-2 rounded-md border-2 border-gray-300 p-2"
                value={entryType}
                onChange={(e) => setEntryType(e.target.value.toLowerCase())}
              >
                <option value="anime">Anime</option>
                <option value="manga">Manga</option>
              </select>
            </label>
            <div className="m-1 flex flex-row items-center justify-start">
              <label htmlFor="sfw" className="m-1">
                SFW
                <input
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  type="checkbox"
                  checked={sfw}
                  onChange={(e) => setSfw(e.target.checked)}
                />
              </label>
              <label htmlFor="nsfw" className="m-1">
                NSFW
                <input
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  type="checkbox"
                  checked={nsfw}
                  onChange={(e) => setNsfw(e.target.checked)}
                />
              </label>
            </div>
            <label htmlFor="approvedStatus" className="m-1">
              Approved Status
              <select
                className="ml-2 rounded-md border-2 border-gray-300 p-2"
                value={approvedStatus}
                onChange={(e) =>
                  setApprovedStatus(e.target.value.toLowerCase())
                }
              >
                <option value="approved">Approved</option>
                <option value="denied">Denied</option>
                <option value="unapproved">Unapproved</option>
                <option value="deleted">Deleted</option>
              </select>
            </label>
            <label htmlFor="limit" className="m-1">
               Per Page
              <select
                className="ml-2 rounded-md border-2 border-gray-300 p-2"
                value={limit}
                onChange={(e) => {
                  setLimit(parseInt(e.target.value));
                  resetPagination();
                }}
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="250">250</option>
                <option value="500">500</option>
                <option value="1000">1000</option>
              </select>
            </label>
          </form>
        </section>
        <section className="flex w-full flex-col items-start justify-center border-2 border-black p-3">
          <ReactPaginate
            breakLabel="..."
            nextLabel={<FontAwesomeIcon icon={faChevronRight} />}
            onPageChange={(e) => setPage(e.selected)}
            pageRangeDisplayed={3}
            pageCount={pageCount.current}
            containerClassName="pagination"
            activeClassName={"item active "}
            breakClassName={"item break-me "}
            pageClassName={"item pagination-page "}
            previousLabel={<FontAwesomeIcon icon={faChevronLeft} />}
          />
        </section>
        <section
          className="flex w-full flex-col  items-center px-4 text-center"
          id="results"
        >
          <div className="flex flex-col items-center justify-center">
            {query.error ? (
              <div className="text-red-500">
                Error: {JSON.stringify(query.error.message)}
              </div>
            ) : query.data ? (
              <div className="container mx-auto">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {query.data.results.map((entry) => (
                    <div key={entry.id}>{entry.title}</div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Loading...</div>
            )}
          </div>
        </section>
      </main>
    </>
  );
};

export default Query;
