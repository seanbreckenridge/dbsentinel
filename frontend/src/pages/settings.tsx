import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";

import NotSignedIn from "../components/NotSignedIn";
import { api } from "../utils/api";

const Settings = () => {
  const { data: session } = useSession();

  const [displayName, setDisplayName] = useState(session?.user?.name || "");
  const updateUsernameMutation = api.settings.updateUsername.useMutation();

  useEffect(() => {
    setDisplayName(session?.user?.name || "");
  }, [session]);

  if (!session) {
    return <NotSignedIn />;
  }

  const mutateDisplayName = () => {
    updateUsernameMutation.mutate({ username: displayName });
  };

  // let user edit their username here
  return (
    <div className="mt-2 flex min-h-screen flex-col items-center">
      <h1 className="text-4xl font-bold">Settings</h1>
      {/* edit username */}
      <form
        className="mt-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutateDisplayName();
        }}
      >
        <label htmlFor="username" className="block text-lg font-bold">
          Display Name
        </label>
        <input
          type="text"
          id="username"
          className="mt-2 rounded-md border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[#2e026d]"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <button
          className="ml-2 mt-4 rounded-md bg-[#2e026d] px-4 py-2 text-white hover:bg-[#15162c]"
          type="submit"
        >
          Save
        </button>
      </form>
      {/* align left */}
      <div className="mt-2 flex flex-col items-start">
        {updateUsernameMutation.isLoading && (
          <span className="ml-2">Saving...</span>
        )}
        {updateUsernameMutation.isSuccess && (
          <span className="ml-2">Saved!</span>
        )}
        {updateUsernameMutation.isError && (
          <span className="ml-2">Error updating username...</span>
        )}
      </div>
    </div>
  );
};

export default Settings;
