export default function Footer() {
  // sticky this to the bottom of the page
  return (
    <footer className="flex flex-col items-center justify-center w-full h-24 border-t">
      <p>
        {
          "this site is not affiliated with MAL, database entry fields (pertaining to anime/manga enties originally from MAL) is property of MAL, see "
        }
        <a
          href="https://myanimelist.net/membership/terms_of_use"
          className="text-blue-400 hover:text-blue-300"
        >
          {"terms of use"}
        </a>
      </p>
      <p>
        {"all other connected data is released under "}
        <a
          href="https://creativecommons.org/share-your-work/public-domain/cc0/"
          className="text-blue-400 hover:text-blue-300"
        >
          {"CC0"}
        </a>
      </p>
      <p>
        {"source code is released under the MIT license "}
        <a
          className="text-blue-400 hover:text-blue-300"
          href="https://github.com/seanbreckenridge/malsentinel"
        >
          here
        </a>
        .
      </p>
    </footer>
  );
}
