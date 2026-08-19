import Link from "next/link";
import { getPlayers } from "@/lib/api";

const POSITIONS = ["GKP", "DEF", "MID", "FWD"] as const;
const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "total_points", label: "Points" },
  { value: "now_cost", label: "Price" },
  { value: "form", label: "Form" },
  { value: "goals_scored", label: "Goals" },
  { value: "assists", label: "Assists" },
  { value: "expected_goals", label: "xG" },
  { value: "expected_assists", label: "xA" },
  { value: "ict_index", label: "ICT Index" },
  { value: "defensive_contribution", label: "DEFCON stat" },
];

function buildHref(params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const qs = search.toString();
  return qs ? `/players?${qs}` : "/players";
}

export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ position?: string; sort?: string; order?: string }>;
}) {
  const { position, sort = "total_points", order = "desc" } = await searchParams;
  const players = await getPlayers({ position, sort, order, limit: 100 });

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-4 text-2xl font-semibold">Players</h1>

      <div className="mb-6 flex flex-wrap items-center gap-4 text-sm">
        <div className="flex gap-2">
          <Link
            href={buildHref({ sort, order })}
            className={`rounded px-3 py-1 ${!position ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800"}`}
          >
            All
          </Link>
          {POSITIONS.map((pos) => (
            <Link
              key={pos}
              href={buildHref({ position: pos, sort, order })}
              className={`rounded px-3 py-1 ${position === pos ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800"}`}
            >
              {pos}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-zinc-500">Sort:</span>
          {SORT_OPTIONS.map((opt) => (
            <Link
              key={opt.value}
              href={buildHref({ position, sort: opt.value, order })}
              className={`rounded px-2 py-1 ${sort === opt.value ? "underline font-medium" : "text-zinc-500"}`}
            >
              {opt.label}
            </Link>
          ))}
          <Link
            href={buildHref({ position, sort, order: order === "desc" ? "asc" : "desc" })}
            className="ml-1 text-zinc-500"
          >
            {order === "desc" ? "↓" : "↑"}
          </Link>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="py-2 pr-4">Player</th>
              <th className="py-2 pr-4">Team</th>
              <th className="py-2 pr-4">Pos</th>
              <th className="py-2 pr-4 text-right">Price</th>
              <th className="py-2 pr-4 text-right">Pts</th>
              <th className="py-2 pr-4 text-right">Form</th>
              <th className="py-2 pr-4 text-right">Goals</th>
              <th className="py-2 pr-4 text-right">Assists</th>
              <th className="py-2 pr-4 text-right">xG</th>
              <th className="py-2 pr-4 text-right">xA</th>
              <th className="py-2 pr-4 text-right">DEFCON stat</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.code} className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-900 dark:hover:bg-zinc-900">
                <td className="py-2 pr-4">
                  <Link href={`/players/${p.code}`} className="hover:underline">
                    {p.web_name}
                  </Link>
                </td>
                <td className="py-2 pr-4 text-zinc-500">{p.team_short_name}</td>
                <td className="py-2 pr-4 text-zinc-500">{p.position}</td>
                <td className="py-2 pr-4 text-right">£{(p.now_cost / 10).toFixed(1)}m</td>
                <td className="py-2 pr-4 text-right font-medium">{p.total_points}</td>
                <td className="py-2 pr-4 text-right">{p.form}</td>
                <td className="py-2 pr-4 text-right">{p.goals_scored}</td>
                <td className="py-2 pr-4 text-right">{p.assists}</td>
                <td className="py-2 pr-4 text-right text-zinc-500">{p.expected_goals ?? "—"}</td>
                <td className="py-2 pr-4 text-right text-zinc-500">{p.expected_assists ?? "—"}</td>
                <td className="py-2 pr-4 text-right text-zinc-500">{p.defensive_contribution ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
