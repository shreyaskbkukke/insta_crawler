import { fmtCount, type Profile } from "@/lib/api";

export function ProfileHeader({ profile }: { profile: Profile }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
      {profile.profile_picture_url ? (
        <img
          src={profile.profile_picture_url}
          alt=""
          referrerPolicy="no-referrer"
          className="size-20 shrink-0 rounded-full bg-neutral-200 object-cover dark:bg-neutral-800"
        />
      ) : (
        <div className="size-20 shrink-0 rounded-full bg-neutral-200 dark:bg-neutral-800" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <h1 className="text-2xl font-semibold tracking-tight">@{profile.username}</h1>
          {profile.display_name && <span className="text-neutral-500">{profile.display_name}</span>}
          <a
            href={profile.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            View on Instagram ↗
          </a>
        </div>
        <div className="mt-1 flex gap-4 text-sm">
          <span>
            <b>{fmtCount(profile.media_count)}</b> posts
          </span>
          <span>
            <b>{fmtCount(profile.followers_count)}</b> followers
          </span>
          <span>
            <b>{fmtCount(profile.follows_count)}</b> following
          </span>
        </div>
        {profile.biography && (
          <p className="mt-2 whitespace-pre-line text-sm text-neutral-700 dark:text-neutral-300">{profile.biography}</p>
        )}
        {profile.website && (
          <a
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            {profile.website.replace(/^https?:\/\//, "")}
          </a>
        )}
      </div>
    </div>
  );
}
