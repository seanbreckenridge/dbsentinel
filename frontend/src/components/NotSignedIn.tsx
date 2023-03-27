import { signIn } from "next-auth/react";

const NotSignedIn = () => {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <h1 className="text-4xl font-bold">You are not signed in</h1>
      <button
        className="mt-4 rounded-md bg-[#2e026d] px-4 py-2 text-white hover:bg-[#15162c]"
        onClick={() => void signIn()}
      >
        Sign in
      </button>
    </div>
  );
};

export default NotSignedIn;
