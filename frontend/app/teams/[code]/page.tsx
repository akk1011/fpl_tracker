import Link from "next/link";
import { notFound } from "next/navigation";
import { getTeam } from "@/lib/api";

export default async function TeamDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;

  let team;
  try {
    team = await getTeam(code);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Link href="/teams" className="text-sm text-zinc-500 hover:underline">
        ← All teams
      </Link>

      <h1 className="mt-2 mb-6 text-2xl font-semibold">{team.name}</h1>

      <div className="mb-8 grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat label="League position" value={team.position || "—"} />
        <Stat label="Played" value={team.played} />
        <Stat label="W / D / L" value={`${team.win} / ${team.draw} / ${team.loss}`} />
        <Stat label="Squad size" value={team.squad_size} />
      </div>

      <h2 className="mb-3 text-lg font-medium">Squad</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-sm">
          <thead className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="py-2 pr-4">Player</th>
              <th className="py-2 pr-4">Pos</th>
              <th className="py-2 pr-4 text-right">Price</th>
              <th className="py-2 pr-4 text-right">Pts</th>
              <th className="py-2 pr-4 text-right">Goals</th>
              <th className="py-2 pr-4 text-right">Assists</th>
            </tr>
          </thead>
          <tbody>
            {team.squad.map((p) => (
              <tr key={p.code} className="border-b border-zinc-100 dark:border-zinc-900">
                <td className="py-2 pr-4">
                  <Link href={`/players/${p.code}`} className="hover:underline">
                    {p.web_name}
                  </Link>
                </td>
                <td className="py-2 pr-4 text-zinc-500">{p.position}</td>
                <td className="py-2 pr-4 text-right">£{(p.now_cost / 10).toFixed(1)}m</td>
                <td className="py-2 pr-4 text-right font-medium">{p.total_points}</td>
                <td className="py-2 pr-4 text-right">{p.goals_scored}</td>
                <td className="py-2 pr-4 text-right">{p.assists}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-lg font-medium">{value}</div>
    </div>
  );
}
