// All fetching in this app happens in Server Components (see the Phase 2
// plan — v1 dashboards are read-only browsing with no client-side
// interactivity), so this runs on Vercel's server, never in the browser.
// That means CORS never applies to these calls, and the backend URL never
// needs to reach the client bundle — hence a plain (non-NEXT_PUBLIC_) env
// var, not the NEXT_PUBLIC_ prefix Next.js reserves for client-exposed vars.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type Player = {
  id: number;
  code: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_short_name: string;
  team_name: string;
  position: "GKP" | "DEF" | "MID" | "FWD";
  now_cost: number;
  total_points: number;
  event_points: number;
  form: string;
  selected_by_percent: string;
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  expected_goals: string | null;
  expected_assists: string | null;
  expected_goals_conceded: string | null;
  ict_index: string | null;
  bonus: number;
  bps: number;
  defensive_contribution: number | null;
  status: string;
  news: string;
};

export type PointsBreakdown = {
  appearance: number;
  goals: number;
  assists: number;
  clean_sheets: number;
  goals_conceded_penalty: number;
  saves: number;
  penalty_saves: number;
  penalty_misses: number;
  cards: number;
  own_goals: number;
  defcon: number;
  bonus: number;
  total: number;
};

export type PlayerDetail = Player & {
  position_full: string;
  clearances_blocks_interceptions: number | null;
  recoveries: number | null;
  tackles: number | null;
  matches_played_this_season: number;
  points_breakdown_this_season: PointsBreakdown;
};

export type PlayerGameweek = {
  gameweek_id: number;
  gameweek_name: string;
  opponent_short_name: string | null;
  was_home: boolean | null;
  total_points: number;
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  defensive_contribution: number | null;
  points_breakdown: PointsBreakdown;
};

export type Team = {
  id: number;
  code: number;
  name: string;
  short_name: string;
  strength: number | null;
  played: number;
  win: number;
  draw: number;
  loss: number;
  points: number;
  position: number;
  squad_size: number;
};

export type SquadMember = {
  id: number;
  code: number;
  web_name: string;
  position: string;
  now_cost: number;
  total_points: number;
  form: string;
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  status: string;
};

export type TeamDetail = Team & { squad: SquadMember[] };

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API request to ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function getPlayers(params: {
  position?: string;
  team?: string;
  sort?: string;
  order?: string;
  limit?: number;
}): Promise<Player[]> {
  const search = new URLSearchParams();
  if (params.position) search.set("position", params.position);
  if (params.team) search.set("team", params.team);
  if (params.sort) search.set("sort", params.sort);
  if (params.order) search.set("order", params.order);
  search.set("limit", String(params.limit ?? 100));
  return apiFetch(`/api/players?${search.toString()}`);
}

export function getPlayer(code: string): Promise<PlayerDetail> {
  return apiFetch(`/api/players/${code}`);
}

export function getPlayerGameweeks(code: string): Promise<PlayerGameweek[]> {
  return apiFetch(`/api/players/${code}/gameweeks`);
}

export function getTeams(): Promise<Team[]> {
  return apiFetch(`/api/teams`);
}

export function getTeam(code: string): Promise<TeamDetail> {
  return apiFetch(`/api/teams/${code}`);
}
