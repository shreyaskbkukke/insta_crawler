import { Suspense } from "react";
import { Explorer } from "@/components/Explorer";

export default function ProfilePage() {
  return (
    <Suspense fallback={<p className="text-neutral-500">Loading…</p>}>
      <Explorer />
    </Suspense>
  );
}
