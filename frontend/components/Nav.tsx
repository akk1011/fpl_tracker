import Link from "next/link";

export default function Nav() {
  return (
    <nav className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-4">
        <Link href="/players" className="text-lg font-semibold">
          FPL Analytics
        </Link>
        <Link href="/players" className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
          Players
        </Link>
        <Link href="/teams" className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
          Teams
        </Link>
      </div>
    </nav>
  );
}
