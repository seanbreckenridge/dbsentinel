import Link from "next/link";

import { signIn, signOut, useSession } from "next-auth/react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear } from "@fortawesome/free-solid-svg-icons";

export default function Navbar() {
  const { data: sessionData } = useSession();

  return (
    <nav className="mx-auto flex w-full flex-wrap items-center bg-teal-500 py-2 px-3">
      <ul className="flex-grow-1 container mx-auto flex w-full items-center p-4">
        <li className="mr-4 text-xl font-bold text-slate-100">
          <Link href="/">Home</Link>
        </li>
        <li className="mr-4 text-xl font-bold text-slate-100">
          <Link href="/search">Search</Link>
        </li>
        <li className="mr-auto text-xl font-bold text-slate-100">
          <Link href="/about">About</Link>
        </li>
        {/* settings icon */}
        {sessionData && (
          <li className="flex-grow-0">
            <Link href="/settings" className="text-slate-100">
              <div
                className="m-2 mr-4 flex h-6 w-6 items-center"
                title="Settings"
                role="button"
              >
                <FontAwesomeIcon icon={faGear} />
              </div>
            </Link>
          </li>
        )}
        {/* login button with border on the right */}
        <li className="border-3 flex flex-grow-0 items-center rounded-md bg-slate-100 p-2 px-3 text-black transition-colors">
          {sessionData ? (
            <button onClick={() => void signOut()}>Sign out</button>
          ) : (
            <button onClick={() => void signIn()}>Sign in</button>
          )}
        </li>
      </ul>
    </nav>
  );
}
