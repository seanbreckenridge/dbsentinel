import { type NextPage } from "next";
import Head from "next/head";
import Image from "next/image";
import { useRouter } from "next/router";
import { useState, useRef, useEffect } from "react";
import ReactPaginate from "react-paginate";
import { type QueryOutput } from "../server/api/routers/data";
import { DebounceInput } from "react-debounce-input";

import Modal from "react-modal";
import dayjs from "dayjs";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronLeft,
  faQuestionCircle,
  faTimes,
} from "@fortawesome/free-solid-svg-icons";

import { api } from "../utils/api";
import {
  animeMediaTypes,
  mangaMediaTypes,
  type AllMediaTypes,
} from "../server/api/routers/mediaTypes";

const ALLOWED_JSON_KEYS = ["num_episodes", "volumes", "chapters"];

const INFO = `APPROVED: current approved MAL entry
UNAPPROVED: submitted by a user, is waiting for moderator approval
DELETED: was previously APPROVED, but has been deleted by a moderator
DENIED: was previously UNAPPROVED, but has been denied by a moderator`;

const DELETED_INFO =
  "These deleted/denied are estimates based on when data was added/last cached, and not necessarily when the entry was deleted/denied.";

// @types-react-paginate is 2 years out of date
interface PaginateSelected {
  selected: number
}

const unslugify = (slug: string) => {
  return slug.split("_").join(" ");
};

const statusLabel = (status: string) => {
  if (status === "unapproved") {
    return "Added on: ";
  } else if (status === "approved") {
    return "Added on: ";
  } else if (status === "denied") {
    return "Denied on: ";
  } else if (status === "deleted") {
    return "Deleted on: ";
  }
};

const displayDate = (date: number) => {
  return dayjs.unix(date).format("MMMM D, YYYY h:mm A");
};

type IMetadata = {
  keyName: string;
  value: string;
};

const MetadataRow = ({ keyName, value }: IMetadata) => {
  return (
    <li className="mx-3 flex flex-row items-center justify-center">
      <div className="mr-1 text-xs">
        {unslugify(keyName)}
        {":"}
      </div>
      <div className="text-xs">{value.toString()}</div>
    </li>
  );
};

Modal.setAppElement("#modal-root");

const customStyles = {
  content: {
    top: "10%",
    left: "10%",
    right: "10%",
    bottom: "10%",
  },
};

const Query: NextPage = () => {
  // form values
  const [title, setTitle] = useState("");
  const [entryType, setEntryType] = useState("anime");
  const [sfw, setSfw] = useState(true);
  const [nsfw, setNsfw] = useState(false);
  const [blurNSFW, setBlurNSFW] = useState(true);
  const [approvedStatus, setApprovedStatus] = useState("all");
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(100);
  const [orderBy, setOrderBy] = useState("id");
  const [sort, setSort] = useState("desc");
  const [filterMediaType, setFilterMediaType] = useState<
    AllMediaTypes | undefined
  >(undefined);

  // modal
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [modalText, setModalText] = useState("");
  const [copyText, setCopyText] = useState("");
  const launchModalWithText = (text: string) => {
    setCopyText("")
    setModalText(text + text + text);
    setModalIsOpen(true);
  };
  const closeModal = () => {
    setModalIsOpen(false)
  }

  const copyModalToClipboard = () => {
    navigator.clipboard
      .writeText(modalText)
      .then(() => {
        setCopyText("copied to clipboard");
      })
      .catch((e) => {
        setCopyText("failed to copy to clipboard, check console for details");
        console.error(e);
      });
  };

  // cant use this immediately, need to wait till the user interacts with the page some
  // without it, the page will constantly reload when the user is typing
  const pageCountRef = useRef(1);
  const usePageRef = useRef(false);

  const router = useRouter();

  const resetPagination = () => {
    setPage(0);
    pageCountRef.current = 1;
  };

  let nsfwQuery = undefined;
  if (sfw) {
    nsfwQuery = false;
  } else if (nsfw) {
    nsfwQuery = true;
  }

  // validate/send user input to backend
  const query = api.data.dataQuery.useQuery(
    {
      entry_type:
        entryType === "anime" || entryType === "manga" ? entryType : undefined,
      title: title.length > 0 ? title : undefined,
      nsfw: nsfwQuery,
      approved_status:
        approvedStatus === "all" ||
        approvedStatus === "approved" ||
        approvedStatus === "denied" ||
        approvedStatus === "unapproved" ||
        approvedStatus === "deleted"
          ? approvedStatus
          : "all",
      offset: page * limit,
      limit: limit,
      order_by:
        orderBy === "id" ||
        orderBy === "title" ||
        orderBy === "start_date" ||
        orderBy === "end_date" ||
        orderBy === "status_updated_at" ||
        orderBy === "metadata_updated_at" ||
        orderBy === "member_count" ||
        orderBy === "average_episode_duration"
          ? orderBy
          : "id",
      sort: sort === "asc" || sort === "desc" ? sort : "desc",
      media_type:
        filterMediaType === undefined
          ? undefined
          : filterMediaType.toLowerCase() == "all"
          ? undefined
          : filterMediaType,
    },
    {
      onSuccess: (data: QueryOutput) => {
        pageCountRef.current = Math.ceil(data.total_count / limit);
      },
    }
  );

  useEffect(() => {
    if (query.data) {
      pageCountRef.current = Math.ceil(query.data.total_count / limit);
    }
  }, [limit, query.data, query.data?.total_count]);

  useEffect(() => {
    const qr = router.query;
    if (qr.entry_type) {
      if (qr.entry_type === "anime" || qr.entry_type === "manga") {
        setEntryType(qr.entry_type);
      }
    }

    if (qr.status) {
      if (
        qr.status === "approved" ||
        qr.status === "denied" ||
        qr.status === "unapproved" ||
        qr.status === "deleted"
      ) {
        setApprovedStatus(qr.status);
      }
    }

    if (qr.sfw) {
      setSfw(true);
    } else if (qr.nsfw) {
      setNsfw(false);
    }

    if (qr.order_by) {
      if (
        qr.order_by === "id" ||
        qr.order_by === "title" ||
        qr.order_by === "start_date" ||
        qr.order_by === "end_date" ||
        qr.order_by === "status_updated_at" ||
        qr.order_by === "metadata_updated_at" ||
        qr.order_by === "metadata_updated_at" ||
        qr.order_by === "member_count"
      ) {
        setOrderBy(qr.order_by);
      }
    }

    if (qr.sort) {
      if (qr.sort === "asc" || qr.sort === "desc") {
        setSort(qr.sort);
      }
    }
  }, [router.query]);

  const pageCount = usePageRef.current
    ? pageCountRef.current
    : query.data
    ? Math.ceil(query.data.total_count / limit)
    : 1;

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
  background-color: #65d6d2;
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
        <Modal
          style={customStyles}
          isOpen={modalIsOpen}
          onRequestClose={closeModal}
          contentLabel="More Info Text"
        >
          <div className="absolute top-5 right-5">
            <div className="flex flex-row">
              <div className="flex flex-col">
                <button
                  className="mr-2 rounded-md border border-black p-2"
                  onClick={copyModalToClipboard}
                >
                  Copy to Clipboard
                </button>
              </div>
              <button
                className="rounded-md border border-[#ff0000] p-2"
                onClick={closeModal}
              >
                Close
              </button>
            </div>
            <div className="pl-2">
              {copyText}
            </div>
          </div>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              wordWrap: "break-word",
            }}
          >
            {modalText}
          </pre>
        </Modal>
        <section className="flex w-full flex-col items-start justify-center p-3">
          <form
            className="flex w-full flex-col items-start justify-center"
            onSubmit={(e) => e.preventDefault()}
          >
            <label htmlFor="title" className="m-1">
              Title
              <DebounceInput
                className="ml-2 rounded-md border-2 border-gray-300 p-2"
                aria-label="Search"
                placeholder="Search..."
                value={title}
                debounceTimeout={500}
                onChange={(e) => {
                  setTitle(e.target.value);
                  usePageRef.current = true;
                  resetPagination();
                }}
              />
            </label>
            <div className="items-left m-1 flex flex-col justify-center sm:flex-row">
              <label htmlFor="entryType" className="m-1">
                Type
                <select
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  value={entryType}
                  onChange={(e) => {
                    setEntryType(e.target.value.toLowerCase());
                    setFilterMediaType(undefined);
                    usePageRef.current = true;
                  }}
                >
                  <option value="anime">Anime</option>
                  <option value="manga">Manga</option>
                </select>
              </label>
              <label htmlFor="approvedStatus" className="m-1">
                <div className="flex flex-row items-center justify-start">
                  <p>Approved Status</p>
                  <div
                    title="info cursor"
                    role="button"
                    className="ml-2"
                    onClick={() => alert(INFO)}
                  >
                    <FontAwesomeIcon
                      icon={faQuestionCircle}
                      className="mx-1 mr-2 h-5 w-5"
                    />
                  </div>
                  <select
                    className="ml-2 rounded-md border-2 border-gray-300 p-2"
                    value={approvedStatus}
                    onChange={(e) => {
                      setApprovedStatus(e.target.value.toLowerCase());
                      usePageRef.current = true;
                    }}
                  >
                    <option value="all">All</option>
                    <option value="approved">Approved</option>
                    <option value="denied">Denied</option>
                    <option value="unapproved">Unapproved</option>
                    <option value="deleted">Deleted</option>
                  </select>
                </div>
              </label>
              <label htmlFor="Media Type" className="m-1">
                Media Type
                <select
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  value={filterMediaType}
                  onChange={(e) => {
                    if (e.target.value.toLowerCase() === "all") {
                      setFilterMediaType(undefined);
                    }
                    setFilterMediaType(e.target.value as AllMediaTypes);
                    usePageRef.current = true;
                  }}
                >
                  <option value="all">all</option>
                  {entryType === "anime"
                    ? animeMediaTypes.map((type) => (
                        <option key={type} value={type}>
                          {unslugify(type)}
                        </option>
                      ))
                    : mangaMediaTypes.map((type) => (
                        <option key={type} value={type}>
                          {unslugify(type)}
                        </option>
                      ))}
                </select>
              </label>
            </div>
            <div className="items-left m-1 flex flex-col justify-center sm:flex-row">
              <label htmlFor="orderBy" className="m-1">
                Order By
                <select
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  value={orderBy}
                  onChange={(e) => {
                    setOrderBy(e.target.value.toLowerCase());
                    usePageRef.current = true;
                  }}
                >
                  <option value="id">ID</option>
                  <option value="title">Title</option>
                  <option value="start_date">Start Date</option>
                  <option value="end_date">End Date</option>
                  <option value="status_updated_at">Status Updated At</option>
                  <option value="metadata_updated_at">
                    Metadata Updated At
                  </option>
                  <option value="member_count">Popularity</option>
                  <option value="average_episode_duration">
                    Episode Duration
                  </option>
                </select>
              </label>
              <label htmlFor="sort" className="m-1">
                Sort
                <select
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value.toLowerCase());
                    usePageRef.current = true;
                  }}
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
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
                    usePageRef.current = true;
                  }}
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                  <option value="250">250</option>
                </select>
              </label>
            </div>
            <div className="m-1 flex flex-row items-center justify-start">
              <label htmlFor="sfw" className="m-1">
                SFW
                <input
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  type="checkbox"
                  checked={sfw}
                  onChange={(e) => {
                    setSfw(e.target.checked);
                    usePageRef.current = true;
                    // i.e.,: if user is selecting sfw, then we want to unselect nsfw
                    if (nsfw) {
                      setNsfw(false);
                    }
                  }}
                />
              </label>
              <label htmlFor="nsfw" className="m-1">
                NSFW
                <input
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  type="checkbox"
                  checked={nsfw}
                  onChange={(e) => {
                    setNsfw(e.target.checked);
                    usePageRef.current = true;
                    if (sfw) {
                      setSfw(false);
                    }
                  }}
                />
              </label>
              <label htmlFor="blurNSFW" className="m-1">
                Blur NSFW
                <input
                  className="ml-2 rounded-md border-2 border-gray-300 p-2"
                  type="checkbox"
                  checked={blurNSFW}
                  onChange={(e) => {
                    setBlurNSFW(e.target.checked);
                    usePageRef.current = true;
                  }}
                />
              </label>
            </div>
          </form>
        </section>
        <hr className="w-full" />
        <section className="flex w-full flex-col items-center justify-center p-3">
          <p className="mb-1">Total Results: {query.data?.total_count}</p>
          <ReactPaginate
            breakLabel="..."
            nextLabel={<FontAwesomeIcon icon={faChevronRight} />}
            onPageChange={(e: never) => {
              setPage((e as PaginateSelected).selected);
              usePageRef.current = true;
            }}
            pageRangeDisplayed={3}
            pageCount={pageCount}
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
          <div className="flex w-full flex-col items-center justify-center">
            {query.error ? (
              <div className="text-red-500">
                Error: {JSON.stringify(query.error.message)}
              </div>
            ) : query.data && query.data.total_count > 0 ? (
              <div className="container mx-auto flex w-full flex-col items-center justify-center">
                <table className="max-w-full table-fixed">
                  <thead>
                    <tr className="border-2 border-black bg-gray-100">
                      <th className="px-2 py-2"></th>
                      <th className="px-2 py-2">Meta</th>
                      <th className="px-2 py-2">Data</th>
                      <th className="cursor flex flex-row items-center justify-center px-2 py-2">
                        <div>Dates</div>
                        <FontAwesomeIcon
                          icon={faQuestionCircle}
                          className="mx-1 mr-2 h-5 w-5 cursor-pointer"
                          title={DELETED_INFO}
                          onClick={() => alert(DELETED_INFO)}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.results.map((entry) => {
                      // TODO: add:
                      // - link to anilist if that exists
                      const img = entry.image_url ?? undefined;
                      return (
                        <tr key={entry.id}>
                          <td className="w-1/12 border">
                            {img ? (
                              <a
                                title="View Image"
                                href={img ? img : "javascript:void(0)"}
                                target="_blank"
                                rel="noreferrer"
                              >
                                <Image
                                  className="mx-auto my-auto"
                                  style={{
                                    filter:
                                      blurNSFW && entry.nsfw === true
                                        ? "blur(5px)"
                                        : "none",
                                  }}
                                  src={img}
                                  alt="..."
                                  width={100}
                                  height={100}
                                  // opt out of image optimization
                                  loader={({ src }) => src}
                                />
                              </a>
                            ) : (
                              <div className="mx-auto my-auto h-4 w-4 ">
                                <FontAwesomeIcon icon={faTimes} />
                              </div>
                            )}
                          </td>
                          <td className="w-1/12 border px-2 py-2">
                            <div className="flex w-full flex-col items-center justify-center">
                              <div>
                                {"ID: "}
                                {entry.approved_status != "denied" &&
                                entry.approved_status != "deleted" ? (
                                  <a
                                    className="text-blue-600"
                                    title="View on MAL"
                                    href={`https://myanimelist.net/${entryType}/${entry.id}`}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    {entry.id}
                                  </a>
                                ) : (
                                  <div>{entry.id}</div>
                                )}
                              </div>
                              <div className="my-1 text-xs">
                                {entry.nsfw === null || entry.nsfw === undefined
                                  ? "Unknown"
                                  : entry.nsfw
                                  ? "NSFW"
                                  : "SFW"}
                              </div>
                              <div className="text-xs">
                                {entry.approved_status}
                              </div>
                            </div>
                          </td>
                          <td className="w-4/12 border px-2 py-2">
                            <div className="flex w-full flex-col items-center justify-center">
                              <div>{entry.title}</div>
                              <hr className="my-2 w-10/12" />
                              <ul className="mb-2 flex w-full flex-col items-center justify-center sm:flex-row">
                                <MetadataRow
                                  keyName="media type"
                                  value={
                                    entry.media_type
                                      ? unslugify(entry.media_type)
                                      : "unknown"
                                  }
                                />
                                <MetadataRow
                                  keyName="members"
                                  value={
                                    entry.member_count
                                      ? entry.member_count.toLocaleString()
                                      : "-"
                                  }
                                />
                                <MetadataRow
                                  keyName="ep duration"
                                  value={
                                    entry.average_episode_duration
                                      ? (entry.average_episode_duration / 60)
                                          .toFixed(0)
                                          .toString() + " min"
                                      : "-"
                                  }
                                />
                              </ul>
                              <ul className="flex w-full flex-col items-center justify-center sm:flex-row">
                                {/* eslint-disable-next-line @typescript-eslint/no-unsafe-argument */}
                                {Object.keys(entry.json_data)
                                  .filter((key: string) =>
                                    ALLOWED_JSON_KEYS.includes(key)
                                  )
                                  .map((key: string) => {
                                    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
                                    const value = entry.json_data[
                                      key
                                    ] as string;
                                    const keyName =
                                      key == "num_episodes" ? "episodes" : key;
                                    return (
                                      <MetadataRow
                                        key={key}
                                        keyName={keyName}
                                        value={value}
                                      />
                                    );
                                  })}
                                <li
                                  className="mx-3 flex flex-row items-center justify-center"
                                  title="Show All Info"
                                >
                                  <a
                                    className="cursor text-xs text-blue-600"
                                    role="button"
                                    onClick={() => {
                                      launchModalWithText(
                                        JSON.stringify(entry, null, 2)
                                      );
                                    }}
                                  >
                                    more info
                                  </a>
                                </li>
                              </ul>
                            </div>
                          </td>
                          <td className="w-2/12 border p-0 sm:p-1 md:p-2">
                            <div className="flex w-full flex-col items-center justify-center">
                              <div className="text-xs">
                                {"Start Date: "}
                                {entry.start_date}
                              </div>
                              <div className="text-xs">
                                {"End Date: "}
                                {entry.end_date}
                              </div>
                              <div className="text-xs">
                                {"Metadata Last Updated: "}
                                {displayDate(entry.metadata_updated_at)}
                              </div>
                              <div className="text-xs">
                                {statusLabel(entry.approved_status)}
                                {displayDate(entry.status_updated_at)}
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : query.data && query.data.total_count === 0 ? (
              <div className="text-red-500">No Results</div>
            ) : (
              <div className="text-gray-500">Loading...</div>
            )}
          </div>
        </section>
        <section className="flex w-full flex-col items-center justify-center p-3">
          <ReactPaginate
            breakLabel="..."
            nextLabel={<FontAwesomeIcon icon={faChevronRight} />}
            onPageChange={(e: never) => {
              setPage((e as PaginateSelected).selected);
              usePageRef.current = true;
            }}
            pageRangeDisplayed={3}
            pageCount={pageCount}
            containerClassName="pagination"
            activeClassName={"item active "}
            breakClassName={"item break-me "}
            pageClassName={"item pagination-page "}
            previousLabel={<FontAwesomeIcon icon={faChevronLeft} />}
          />
        </section>
      </main>
    </>
  );
};

export default Query;
