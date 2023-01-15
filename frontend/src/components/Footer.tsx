export default function Footer() {
  // sticky this to the bottom of the page
  return (
    <footer className="h-30 my-5 flex w-full flex-col items-center justify-center border-t text-sm">
      <p>
        {`${new Date().getFullYear()} © malsentinel `}
        <a
          className="text-blue-400 hover:text-blue-300"
          href="https://github.com/seanbreckenridge/malsentinel"
        >
          source code
        </a>
      </p>
    </footer>
  );
}
