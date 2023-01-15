import Link from "next/link";

import { signIn, signOut, useSession } from "next-auth/react";

export default function Navbar() {
  const { data: sessionData } = useSession();

  return (
    <nav className="mx-auto flex items-center flex-wrap bg-teal-500 py-2 px-3">
      <ul className="container mx-auto flex items-center p-4 w-full">
        <li className="text-xl font-bold text-slate-100">
          <Link href="/">Home</Link>
        </li>
        {/* login button with border on the right */}
        <li className="flex items-center border-3 transition-colors text-black p-2 px-3 ml-auto bg-slate-100 rounded-md">
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
