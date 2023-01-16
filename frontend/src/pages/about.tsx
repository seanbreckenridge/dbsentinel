// about page
import React from "react";

export default function About() {
  return (
    <div className="container mx-auto">
      <div>
        <h1 className="mt-2 text-3xl">About</h1>
      </div>
      <h2 className="mt-2 text-2xl">Goals</h2>
      <ul className="list-inside list-disc">
        <li className="ml-4">
          Index{" "}
          <a className="text-blue-600" href="https://myanimelist.net/">
            MyAnimeList
          </a>
          {" unapproved anime/manga"}
        </li>
        <li className="ml-4">
          Save/keep track of deleted/denied (user-submitted entries which are
          denied by MAL staff, which has been happening more as of late), so the
          data is not lost forever
        </li>
        <li className="ml-4">
          Connect to AniList to potentially enrich data (e.g., mapping between
          countryOrigin AniList fields and clubs on MAL)
        </li>
        <li className="ml-4">
          Letting users login/upload XML files from their MAL account, and doing
          interesting things (e.g. finding which anime/manga they do not have on
          their list. Perhaps even letting people list deleted/denied entries
          here, as a way to keep track of them)
        </li>
      </ul>
      <h2 className="mt-2 text-2xl">Data Sources</h2>
      This is an amalgamation of lots of data:
      <ul className="list-inside list-disc">
        <li className="ml-4">
          <a
            className="text-blue-600"
            href="https://github.com/seanbreckenridge/mal-id-cache"
          >
            mal-id-cache
          </a>{" "}
          git history, which is now backfilled from{" "}
          <a
            className="text-blue-600"
            href="https://github.com/Hiyori-API/checker_mal"
          >
            checker_mal
          </a>
          . checker_mal also indexes the unapproved data, which this pings
          periodically to grab/find new approved entries from MAL
        </li>
        <li className="ml-4">
          <a href="https://cal.syoboi.jp/" className="text-blue-600">
            Syoboi Calendar
          </a>{" "}
          info from{" "}
          <a
            className="text-blue-600"
            href="https://github.com/kawaiioverflow/arm"
          >
            kawaiioverflow/arm
          </a>
        </li>
        <li className="ml-4">
          Cached{" "}
          <a className="text-blue-600" href="https://myanimelist.net">
            MyAnimeList
          </a>
          /
          <a className="text-blue-600" href="https://anilist.co/">
            AniList
          </a>{" "}
          requests using{" "}
          <a
            className="text-blue-600"
            href="https://github.com/seanbreckenridge/url_cache"
          >
            url_cache
          </a>
        </li>
      </ul>
      <h3 className="mt-2 text-2xl">Attribution</h3>
      <ul className="list-inside list-disc">
        This is not affiliated/endorsed by MyAnimeList.net, AniList.co, or any
        other anime/manga related sites, and is not intended to be used for any
        commercial purposes -- its to archive deleted/denied/unapproved entries,
        and potentially enrich data/improve the data available on all database
        sites
      </ul>
    </div>
  );
}
