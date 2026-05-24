import { createClient } from "@supabase/supabase-js";
import type {
  AppUser,
  JobOfferSearchFilters,
  JobOfferSearchResult,
  JobsOverview,
  LocationOption,
  MajorDetail,
  QueryState,
  RankRecord,
  Recommendation,
  PublicPositionResult,
  SchoolDetail,
  SchoolProfileRow,
  Subject,
} from "./types";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured =
  Boolean(supabaseUrl && supabaseAnonKey) &&
  !supabaseUrl?.includes("your-project") &&
  !supabaseAnonKey?.includes("your-anon-key");

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl!, supabaseAnonKey!, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    })
  : null;

export async function loginOrRegisterAppUser(phone: string): Promise<AppUser> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("login_or_register_app_user", {
    p_phone: phone.trim(),
  });

  if (error) throw error;
  return data as AppUser;
}

export async function fetchRank(query: QueryState): Promise<RankRecord | null> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。请在 frontend/.env.local 中填写 VITE_SUPABASE_URL 和 VITE_SUPABASE_ANON_KEY。");
  }

  const { data, error } = await supabase.rpc("get_rank_record", {
    p_year: query.year,
    p_subject: query.subject,
    p_score: query.score,
  });

  if (error) throw error;
  return Array.isArray(data) && data.length > 0 ? (data[0] as RankRecord) : null;
}

export async function fetchRecommendations(query: QueryState, rank: number): Promise<Recommendation[]> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("recommend_admissions", {
    p_year: query.year,
    p_subject: query.subject,
    p_user_rank: rank,
    p_query: query.keyword.trim(),
    p_risk: query.risk,
    p_tag: query.tag,
    p_limit: query.pageSize,
    p_offset: (query.page - 1) * query.pageSize,
    p_provinces: query.provinces,
    p_cities: query.cities,
  });

  if (error) throw error;
  return (data || []) as Recommendation[];
}

export async function fetchLocationOptions(): Promise<LocationOption[]> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("location_options");
  if (error) throw error;
  return (data || []) as LocationOption[];
}

export async function fetchSchoolProfile(schoolQuery: string, subject: Subject): Promise<SchoolProfileRow[]> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("get_school_profile", {
    p_school_query: schoolQuery.trim(),
    p_subject: subject,
  });

  if (error) throw error;
  return (data || []) as SchoolProfileRow[];
}

export async function fetchSchoolDetail(schoolQuery: string, subject: Subject): Promise<SchoolDetail | null> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("get_school_detail", {
    p_school_query: schoolQuery.trim(),
    p_subject: subject,
  });

  if (error) throw error;
  if (!data || (typeof data === "object" && Object.keys(data as Record<string, unknown>).length === 0)) return null;
  return data as SchoolDetail;
}

export async function fetchMajorDetail(
  majorQuery: string,
  schoolQuery: string,
  subject: Subject,
  degreeLevel = "本科",
): Promise<MajorDetail | null> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("get_major_detail", {
    p_major_query: majorQuery.trim(),
    p_school_query: schoolQuery.trim(),
    p_subject: subject,
    p_degree_level: degreeLevel,
  });

  if (error) throw error;
  if (!data || (typeof data === "object" && Object.keys(data as Record<string, unknown>).length === 0)) return null;
  return data as MajorDetail;
}

export async function fetchJobsOverview(): Promise<JobsOverview> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("get_jobs_overview");
  if (error) throw error;
  return (data || { schoolCount: 0, majorCount: 0, recordCount: 0, byCategory: [], latestRecords: [] }) as JobsOverview;
}

export async function searchJobOffers(filters: JobOfferSearchFilters): Promise<JobOfferSearchResult> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("search_job_offers", {
    p_school_query: filters.schoolQuery.trim(),
    p_major_query: filters.majorQuery.trim(),
    p_degree_level: filters.degreeLevel,
    p_data_year: filters.dataYear,
    p_company_query: filters.companyQuery.trim(),
    p_limit: filters.limit,
    p_offset: filters.offset,
  });

  if (error) throw error;
  return (data || { total: 0, records: [] }) as JobOfferSearchResult;
}

export async function fetchPublicPositionsByMajor(
  majorQuery: string,
  includeLow: boolean,
  limit = 80,
): Promise<PublicPositionResult> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase.rpc("search_public_positions_by_major", {
    p_major_query: majorQuery.trim(),
    p_include_low: includeLow,
    p_limit: limit,
  });

  if (error) throw error;
  return (data || { civilServiceTotal: 0, militaryCivilianTotal: 0, civilService: [], militaryCivilian: [] }) as PublicPositionResult;
}

export interface VolunteerListRecord {
  id: string;
  title: string;
  items: Recommendation[];
  updated_at: string;
}

export async function fetchLatestVolunteerList(deviceId: string): Promise<VolunteerListRecord | null> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const { data, error } = await supabase
    .from("volunteer_lists")
    .select("id,title,items,updated_at")
    .eq("device_id", deviceId)
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) throw error;
  return data as VolunteerListRecord | null;
}

export async function saveVolunteerList(deviceId: string, items: Recommendation[]): Promise<VolunteerListRecord> {
  if (!supabase) {
    throw new Error("Supabase 尚未配置。");
  }

  const latest = await fetchLatestVolunteerList(deviceId);
  const payload = {
    title: "我的志愿表",
    items,
    updated_at: new Date().toISOString(),
  };

  if (latest) {
    const { data, error } = await supabase
      .from("volunteer_lists")
      .update(payload)
      .eq("id", latest.id)
      .select("id,title,items,updated_at")
      .single();
    if (error) throw error;
    return data as VolunteerListRecord;
  }

  const { data, error } = await supabase
    .from("volunteer_lists")
    .insert({ ...payload, device_id: deviceId })
    .select("id,title,items,updated_at")
    .single();

  if (error) throw error;
  return data as VolunteerListRecord;
}
