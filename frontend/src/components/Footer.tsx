export default function Footer() {
  // sticky this to the bottom of the page
  return (
    <footer className="h-30 my-5 flex w-full flex-col items-center justify-center border-t text-sm">
      <p>
        {`${new Date().getFullYear()} © dbsentinel `}
        <a
          className="text-blue-600 hover:text-blue-700"
          href="https://github.com/seanbreckenridge/dbsentinel"
        >
          source code
        </a>
      </p>
    </footer>
  );
}
