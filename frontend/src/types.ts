export type Subject = "physics" | "history";
export type RiskType = "all" | "reach" | "match" | "safe";

export interface RankRecord {
  year: number;
  subject: Subject;
  score: number;
  count_at_score: number;
  cumulative_rank: number;
  score_label: string;
}

export interface Recommendation {
  id: number;
  year: number;
  subject: Subject;
  school_code: string;
  school_name: string;
  school_tags: string[];
  province: string | null;
  city: string | null;
  campus_city: string | null;
  major_code: string;
  major_name: string;
  min_score: number;
  min_rank: number;
  admission_type: string;
  remark: string;
  history_years: number;
  best_rank: number;
  worst_rank: number;
  avg_rank: number;
  basis_rank: number;
  rank_diff: number;
  risk_type: Exclude<RiskType, "all">;
  history: Array<{
    year: number;
    min_score: number | null;
    min_rank: number | null;
  }>;
  total_count: number;
}

export interface LocationOption {
  province: string;
  cities: string[];
}

export interface SchoolProfileRow {
  school_name: string;
  school_tags: string[];
  province: string | null;
  city: string | null;
  campus_city: string | null;
  major_code: string;
  major_name: string;
  latest_year: number;
  latest_score: number;
  latest_rank: number;
  history_years: number;
  history: Array<{
    year: number;
    min_score: number | null;
    min_rank: number | null;
    major_code?: string | null;
  }>;
}

export interface DataSource {
  id: number;
  source_key: string;
  source_name: string;
  source_type: string;
  source_year: number | null;
  source_url: string | null;
  credibility: "高" | "中" | "参考" | "待核实";
  update_frequency: string | null;
  notes: string | null;
}

export interface SchoolProfile {
  school_code: string;
  school_name: string;
  school_name_normalized: string;
  school_tags: string[];
  province: string | null;
  city: string | null;
  campus_city: string | null;
  city_tier: string | null;
  school_type: string | null;
  ownership: string | null;
  is_985: boolean;
  is_211: boolean;
  is_double_first_class: boolean;
  double_first_class_subjects: string[];
  has_postgrad_recommend: boolean | null;
  postgrad_recommend_rate: number | null;
  postgrad_destinations: string[];
  notes: string | null;
}

export interface SchoolRanking {
  ranking_name: string;
  ranking_year: number;
  rank_no: number | null;
  rank_label: string | null;
}

export interface DisciplineEvaluation {
  discipline_name: string;
  evaluation_round: string;
  evaluation_grade: string;
}

export interface SchoolAdmissionTrend {
  year: number;
  min_score: number | null;
  best_rank: number | null;
  worst_rank: number | null;
  major_count: number;
}

export interface SchoolDetail {
  profile?: SchoolProfile;
  rankings: SchoolRanking[];
  disciplines: DisciplineEvaluation[];
  admissionTrend: SchoolAdmissionTrend[];
  jobCoverage: number;
}

export interface MajorProfile {
  major_code: string;
  major_name: string;
  discipline_category: string | null;
  major_category: string | null;
  degree_type: string | null;
  standard_duration: string | null;
  subject_requirement: string | null;
  industry_outlook: string | null;
  description: string | null;
  job_directions: string[];
  typical_employers: string[];
  further_study_directions: string[];
  knowledge_source_note?: string | null;
  knowledge_credibility?: string | null;
}

export interface SchoolMajorProfile {
  school_code: string;
  major_code: string;
  school_name: string;
  major_name: string;
  subject_requirement: string | null;
  discipline_grade: string | null;
  notes: string | null;
}

export interface JobRecord {
  id: number;
  school_code: string | null;
  school_name: string;
  major_code: string | null;
  major_name: string;
  degree_level: string;
  job_directions: string[];
  employers: string[];
  employer_tiers: string[];
  monthly_salary_min: number | null;
  monthly_salary_max: number | null;
  annual_bonus_min: number | null;
  annual_bonus_max: number | null;
  first_year_income_min: number | null;
  first_year_income_max: number | null;
  employment_city: string | null;
  data_year: number | null;
  source_url: string | null;
  credibility: "高" | "中" | "待核实";
  verification_status: "verified" | "reviewed" | "pending";
  offer_index: number | null;
  company_name_raw: string | null;
  company_name_standard: string | null;
  company_verification_status: "高" | "中" | "待核实";
  salary_verification_status: "verified" | "reviewed" | "pending";
  video_filename: string | null;
  extraction_notes: string | null;
  notes: string | null;
  created_at: string;
}

export interface MajorSchoolCompareRow {
  school_code: string;
  school_name: string;
  major_name: string;
  best_rank: number | null;
  worst_rank: number | null;
  history_years: number;
}

export interface MajorDetail {
  profile?: MajorProfile;
  schoolMajor?: SchoolMajorProfile;
  jobs: JobRecord[];
  schoolCompare: MajorSchoolCompareRow[];
}

export interface JobsOverview {
  schoolCount: number;
  majorCount: number;
  recordCount: number;
  byCategory: Array<{
    category: string;
    record_count: number;
  }>;
  latestRecords: JobRecord[];
}

export interface JobOfferSearchFilters {
  schoolQuery: string;
  majorQuery: string;
  degreeLevel: string;
  dataYear: number | null;
  companyQuery: string;
  limit: number;
  offset: number;
}

export interface JobOfferSearchResult {
  total: number;
  records: JobRecord[];
}

export interface PublicPositionMatchItem {
  match_level: "high" | "medium" | "low";
  match_type: string;
  match_reason: string;
  position: Record<string, unknown>;
}

export interface PublicPositionResult {
  civilServiceTotal: number;
  militaryCivilianTotal: number;
  civilService: PublicPositionMatchItem[];
  militaryCivilian: PublicPositionMatchItem[];
}

export interface QueryState {
  year: number;
  subject: Subject;
  score: number;
  keyword: string;
  risk: RiskType;
  tag: string;
  provinces: string[];
  cities: string[];
  page: number;
  pageSize: number;
}
