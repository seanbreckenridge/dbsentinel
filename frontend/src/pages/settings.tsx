import { useSession } from "next-auth/react";
import { useState } from "react";

import NotSignedIn from "../components/NotSignedIn";
import { api } from "../utils/api";

const Settings = () => {
  const { data: session } = useSession();

  // strategy is to use undefined to mean user hasnt entered anything yet
  // fallback to remote state if they havent, else use local state
  //
  // if undefined is sent to trpc, it will be ignored
  const [displayName, setDisplayName] = useState<string | undefined>(undefined);
  const [username, setUsername] = useState<string | undefined>(undefined);
  const [error, setError] = useState("");

  const me = api.user.me.useQuery();
  const updateSettingsMutation = api.settings.updateSettings.useMutation();

  if (!session) {
    return <NotSignedIn />;
  }

  const mutateDisplayName = () => {
    updateSettingsMutation.mutate({ name: displayName, username: username });
  };

  // let user edit their username here
  return (
    <div className="mt-2 flex min-h-screen flex-col items-center">
      <h1 className="text-4xl font-bold">Settings</h1>
      <form
        className="mt-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutateDisplayName();
        }}
      >
        <label htmlFor="displayName" className="block text-lg font-bold">
          Display Name
        </label>
        <input
          type="text"
          id="displayName"
          className="mt-2 rounded-md border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[#2e026d]"
          value={displayName ?? me.data?.name ?? ""}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <label htmlFor="username" className="block text-lg font-bold">
          Username
        </label>
        <input
          type="text"
          id="username"
          className="mt-2 rounded-md border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[#2e026d]"
          value={username ?? me.data?.username ?? ""}
          onChange={(e) => {
            setUsername(e.target.value);
            if (e.target.value.length >= 4 && e.target.value.length <= 30) {
              setError("");
            } else {
              setError("Username must be between 4 and 30 characters");
            }
          }}
        />
        <button
          className="ml-2 mt-4 rounded-md bg-[#2e026d] px-4 py-2 text-white hover:bg-[#15162c]"
          type="submit"
          disabled={updateSettingsMutation.isLoading}
        >
          Save
        </button>
      </form>
      <div className="mt-2 flex flex-col items-start">
        {error && <p className="text-red-500">{error}</p>}
        {updateSettingsMutation.isLoading && (
          <span className="ml-2">Saving...</span>
        )}
        {updateSettingsMutation.isSuccess && (
          <span className="ml-2">Saved!</span>
        )}
        {updateSettingsMutation.isError && (
          <span className="ml-2 text-red-500">
            {updateSettingsMutation.error.message.includes(
              `Unique constraint failed on the`
            )
              ? `Username already taken`
              : `Something went wrong updating your settings`}
          </span>
        )}
      </div>
    </div>
  );
};

export default Settings;
