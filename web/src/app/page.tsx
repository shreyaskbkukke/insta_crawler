import { SearchForm } from "@/components/SearchForm";

export default function Home() {
  return (
    <div className="mx-auto max-w-xl pt-16">
      <h1 className="text-3xl font-semibold tracking-tight">Explore an Instagram profile</h1>
      <p className="mt-2 text-neutral-600 dark:text-neutral-400">
        Collect a Business or Creator account&apos;s posts, browse and filter them, and download the data as CSV.
      </p>
      <div className="mt-8">
        <SearchForm />
      </div>
      <p className="mt-4 text-xs text-neutral-500">
        Only public Business/Creator accounts are reachable through the Instagram Graph API. Personal accounts can&apos;t
        be collected.
      </p>
    </div>
  );
}
