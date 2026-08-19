import Link from "next/link";
import { notFound } from "next/navigation";
import { getPlayer, getPlayerGameweeks } from "@/lib/api";

const BREAKDOWN_LABELS: Record<string, string> = {
  appearance: "Appearance",
  goals: "Goals",
  assists: "Assists",
  clean_sheets: "Clean sheets",
  goals_conceded_penalty: "Goals conceded",
  saves: "Saves",
  penalty_saves: "Penalty saves",
  penalty_misses: "Penalty misses",
  cards: "Cards",
  own_goals: "Own goals",
  defcon: "DEFCON",
  bonus: "Bonus",
};

export default async function PlayerDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;

  let player;
  try {
    player = await getPlayer(code);
  } catch {
    notFound();
  }

  const gameweeks = await getPlayerGameweeks(code);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Link href="/players" className="text-sm text-zinc-500 hover:underline">
        ← All players
      </Link>

      <div className="mt-2 mb-8 flex items-baseline gap-3">
        <h1 className="text-2xl font-semibold">{player.web_name}</h1>
        <span className="text-zinc-500">
          {player.team_name} · {player.position_full} · £{(player.now_cost / 10).toFixed(1)}m
        </span>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-6 md:grid-cols-4">
        <Stat label="Season points (recorded)" value={player.total_points} />
        <Stat label="Minutes" value={player.minutes} />
        <Stat label="Goals / Assists" value={`${player.goals_scored} / ${player.assists}`} />
        <Stat label="Clean sheets" value={player.clean_sheets} />
        <Stat label="xG" value={player.expected_goals ?? "—"} />
        <Stat label="xA" value={player.expected_assists ?? "—"} />
        <Stat label="xGC" value={player.expected_goals_conceded ?? "—"} />
        <Stat label="ICT Index" value={player.ict_index ?? "—"} />
      </div>

      <section className="mb-8 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="mb-1 text-lg font-medium">Points breakdown — this season</h2>
        <p className="mb-4 text-sm text-zinc-500">
          Computed from {player.matches_played_this_season} match
          {player.matches_played_this_season === 1 ? "" : "es"} played so far this season — not
          the recorded season-total above, which (before this season&apos;s first gameweek) still
          reflects last season&apos;s final total.
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
          {Object.entries(BREAKDOWN_LABELS).map(([key, label]) => (
            <div key={key} className="flex justify-between border-b border-zinc-100 py-1 dark:border-zinc-900">
              <span className="text-zinc-500">{label}</span>
              <span>{player.points_breakdown_this_season[key as keyof typeof player.points_breakdown_this_season]}</span>
            </div>
          ))}
          <div className="col-span-2 flex justify-between border-b border-zinc-300 py-1 font-medium sm:col-span-4 dark:border-zinc-700">
            <span>Total</span>
            <span>{player.points_breakdown_this_season.total}</span>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Gameweek history</h2>
        {gameweeks.length === 0 ? (
          <p className="text-sm text-zinc-500">No gameweeks played yet this season.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-sm">
              <thead className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
                <tr>
                  <th className="py-2 pr-4">GW</th>
                  <th className="py-2 pr-4">Opponent</th>
                  <th className="py-2 pr-4 text-right">Mins</th>
                  <th className="py-2 pr-4 text-right">Pts</th>
                  <th className="py-2 pr-4 text-right">Goals</th>
                  <th className="py-2 pr-4 text-right">Assists</th>
                  <th className="py-2 pr-4 text-right">DEFCON stat</th>
                </tr>
              </thead>
              <tbody>
                {gameweeks.map((gw) => (
                  <tr key={gw.gameweek_id} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="py-2 pr-4">{gw.gameweek_name}</td>
                    <td className="py-2 pr-4 text-zinc-500">
                      {gw.opponent_short_name ?? "—"} {gw.was_home ? "(H)" : "(A)"}
                    </td>
                    <td className="py-2 pr-4 text-right">{gw.minutes}</td>
                    <td className="py-2 pr-4 text-right font-medium">{gw.total_points}</td>
                    <td className="py-2 pr-4 text-right">{gw.goals_scored}</td>
                    <td className="py-2 pr-4 text-right">{gw.assists}</td>
                    <td className="py-2 pr-4 text-right text-zinc-500">{gw.defensive_contribution ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
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
