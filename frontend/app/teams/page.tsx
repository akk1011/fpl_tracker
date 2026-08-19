import Link from "next/link";
import { getTeams } from "@/lib/api";

export default async function TeamsPage() {
  const teams = await getTeams();

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">Teams</h1>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {teams.map((team) => (
          <Link
            key={team.code}
            href={`/teams/${team.code}`}
            className="rounded-lg border border-zinc-200 p-4 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
          >
            <div className="font-medium">{team.name}</div>
            <div className="text-sm text-zinc-500">{team.squad_size} players</div>
          </Link>
        ))}
      </div>
    </main>
  );
}
