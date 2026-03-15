import { supabase } from "@/lib/supabase";

export interface SearchHistoryResultData {
  pointsByRange: Record<number, { date: string; close: number | null }[]>;
  analysis: {
    data?: Record<string, unknown>[];
    signal?: string;
    latest_price?: number;
    score?: number | null;
  } | null;
  qualitative: {
    qualitative_summary?: string;
    headlines?: { title?: string; link?: string; published_at?: string; image_url?: string }[];
  } | null;
  quantitative: {
    quantitative_summary?: string;
    latest_metrics?: Record<string, unknown>;
  } | null;
  rating: { score: number } | null;
}

export interface SearchHistoryEntry {
  id: string;
  user_id: string;
  symbol: string;
  mode: string;
  company_name: string | null;
  result_data: SearchHistoryResultData;
  created_at: string;
}

export async function saveSearchHistory(
  userId: string,
  symbol: string,
  mode: string,
  companyName: string | null,
  resultData: SearchHistoryResultData
): Promise<{ error: Error | null }> {
  if (!supabase) return { error: new Error("Supabase not configured") };

  const { error } = await supabase.from("search_history").insert({
    user_id: userId,
    symbol: symbol.toUpperCase(),
    mode,
    company_name: companyName,
    result_data: resultData,
  });

  return { error: error ? new Error(error.message) : null };
}

export async function getSearchHistory(userId: string): Promise<{
  data: SearchHistoryEntry[] | null;
  error: Error | null;
}> {
  if (!supabase) return { data: null, error: new Error("Supabase not configured") };

  const { data, error } = await supabase
    .from("search_history")
    .select("id, user_id, symbol, mode, company_name, result_data, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) return { data: null, error: new Error(error.message) };
  return { data: data as SearchHistoryEntry[], error: null };
}

export async function getSearchHistoryEntry(
  userId: string,
  id: string
): Promise<{ data: SearchHistoryEntry | null; error: Error | null }> {
  if (!supabase) return { data: null, error: new Error("Supabase not configured") };

  const { data, error } = await supabase
    .from("search_history")
    .select("id, user_id, symbol, mode, company_name, result_data, created_at")
    .eq("user_id", userId)
    .eq("id", id)
    .single();

  if (error) return { data: null, error: new Error(error.message) };
  return { data: data as SearchHistoryEntry, error: null };
}

export async function deleteSearchHistoryEntry(
  userId: string,
  id: string
): Promise<{ error: Error | null }> {
  if (!supabase) return { error: new Error("Supabase not configured") };

  const { error } = await supabase
    .from("search_history")
    .delete()
    .eq("user_id", userId)
    .eq("id", id);

  return { error: error ? new Error(error.message) : null };
}
