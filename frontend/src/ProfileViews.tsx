import { useEffect, useState } from "react";
import { fetchMajorDetail, fetchPublicPositionsByMajor, fetchSchoolDetail, searchJobOffers } from "./supabase";
import type {
  JobOfferSearchFilters,
  JobOfferSearchResult,
  JobRecord,
  MajorDetail,
  PublicPositionMatchItem,
  PublicPositionResult,
  SchoolDetail,
  Subject,
} from "./types";

function formatNumber(value: number | null | undefined) {
  return value == null ? "-" : value.toLocaleString("zh-CN");
}

function formatMoney(value: number | null | undefined) {
  if (value == null) return "-";
  if (value >= 10000) return `${(value / 10000).toFixed(value % 10000 === 0 ? 0 : 1)}万`;
  return `${value.toLocaleString("zh-CN")}元`;
}

function joinList(values: string[] | null | undefined, fallback = "-") {
  const cleaned = (values || []).filter(Boolean);
  return cleaned.length ? cleaned.join("、") : fallback;
}

export function SalaryChart({ records }: { records: JobRecord[] }) {
  const visible = records
    .filter((record) => record.first_year_income_min || record.monthly_salary_min)
    .slice()
    .sort((a, b) => (b.first_year_income_min ?? 0) - (a.first_year_income_min ?? 0));
  const maxValue = Math.max(...visible.map((record) => record.first_year_income_max ?? record.first_year_income_min ?? 0), 1);

  if (!visible.length) {
    return <div className="empty compact-empty">暂无可视化薪资样本。</div>;
  }

  return (
    <div className="salary-chart">
      {visible.map((record) => {
        const min = record.first_year_income_min ?? 0;
        const max = record.first_year_income_max ?? min;
        const left = Math.max(0, (min / maxValue) * 100);
        const width = Math.max(4, ((max - min) / maxValue) * 100);
        return (
          <div className="salary-row" key={record.id}>
            <div className="salary-label">
              <strong>{record.school_name}</strong>
              <span>{record.major_name} · {record.degree_level}</span>
            </div>
            <div className="salary-track" title={`${formatMoney(min)} - ${formatMoney(max)}`}>
              <span style={{ left: `${left}%`, width: `${width}%` }} />
            </div>
            <b>{formatMoney(min)} - {formatMoney(max)}</b>
          </div>
        );
      })}
    </div>
  );
}

function jobGroupKey(record: JobRecord) {
  return [
    record.school_name,
    record.major_name,
    record.degree_level,
    record.data_year || "年份待补充",
  ].join("|");
}

function groupJobOffers(records: JobRecord[]) {
  const groups: JobRecord[][] = [];
  const index = new Map<string, JobRecord[]>();

  records.forEach((record) => {
    const key = jobGroupKey(record);
    let group = index.get(key);
    if (!group) {
      group = [];
      index.set(key, group);
      groups.push(group);
    }
    group.push(record);
  });

  return groups.map((group) => group.slice().sort((a, b) => (a.offer_index ?? 99) - (b.offer_index ?? 99)));
}

export function JobOfferGroupCard({ records }: { records: JobRecord[] }) {
  const first = records[0];
  const sortedRecords = records.slice().sort((a, b) => (a.offer_index ?? 99) - (b.offer_index ?? 99));

  return (
    <article className="job-group-card">
      <header className="job-group-head">
        <h4>{first.school_name}</h4>
        <p>{first.major_name} · {first.degree_level} · {first.data_year || "年份待补充"}</p>
      </header>
      <div className="offer-list">
        {sortedRecords.map((record) => <JobDataCard key={record.id} record={record} />)}
      </div>
    </article>
  );
}

function JobDataCard({ record }: { record: JobRecord }) {
  const companyName = record.company_name_standard || record.employers?.[0] || "企业待补充";
  const rawCompany = record.company_name_raw && record.company_name_raw !== companyName ? record.company_name_raw : "";
  const workContent = record.job_directions?.[0] || "工作内容待补充";

  return (
    <div className="job-card">
      <div className="job-card-head">
        <div>
          <h4>Offer {record.offer_index || "-"} · {companyName}</h4>
          {rawCompany && <p>原始识别：{rawCompany}</p>}
        </div>
      </div>
      <div className="job-card-grid">
        <div>
          <span>工作内容</span>
          <b>{workContent}</b>
        </div>
        <div>
          <span>工作城市</span>
          <b>{record.employment_city || "待补充"}</b>
        </div>
        <div>
          <span>月薪</span>
          <b>{formatMoney(record.monthly_salary_min)}</b>
        </div>
        <div>
          <span>年终奖</span>
          <b>{formatMoney(record.annual_bonus_min)}</b>
        </div>
        <div>
          <span>首年收入</span>
          <b>{formatMoney(record.first_year_income_min)}</b>
        </div>
      </div>
      {record.source_url && (
        <a className="source-link" href={record.source_url} target="_blank" rel="noreferrer">
          查看来源
        </a>
      )}
    </div>
  );
}

function matchLevelLabel(level: string) {
  if (level === "high") return "高可信";
  if (level === "medium") return "中可信";
  return "低可信";
}

function textValue(position: Record<string, unknown>, key: string) {
  const value = position[key];
  if (value == null || value === "") return "-";
  return String(value);
}

function PublicPositionCard({ item, source }: { item: PublicPositionMatchItem; source: "civil" | "military" }) {
  const p = item.position;
  const title =
    source === "civil"
      ? `${textValue(p, "department")} · ${textValue(p, "position_name")}`
      : `${textValue(p, "employer_name")} · ${textValue(p, "position_name")}`;
  const requirement = source === "civil" ? textValue(p, "major_requirement") : textValue(p, "major_requirement");

  return (
    <article className="public-position-card">
      <div className="public-position-head">
        <h5>{title}</h5>
        <span className={`match-level match-${item.match_level}`}>{matchLevelLabel(item.match_level)}</span>
      </div>
      <div className="public-position-grid">
        {source === "civil" ? (
          <>
            <div><span>考区</span><b>{textValue(p, "exam_area")}</b></div>
            <div><span>单位</span><b>{textValue(p, "unit_name")}</b></div>
            <div><span>招录人数</span><b>{textValue(p, "recruit_count")}</b></div>
            <div><span>学历/学位</span><b>{textValue(p, "education_min")} / {textValue(p, "degree_min")}</b></div>
            <div><span>申论类型</span><b>{textValue(p, "essay_type")}</b></div>
          </>
        ) : (
          <>
            <div><span>岗位类别</span><b>{textValue(p, "position_category")}</b></div>
            <div><span>工作地点</span><b>{textValue(p, "work_location")}</b></div>
            <div><span>招考数量</span><b>{textValue(p, "recruit_count")}</b></div>
            <div><span>学历/学位</span><b>{textValue(p, "education")} / {textValue(p, "degree")}</b></div>
            <div><span>考试科目</span><b>{textValue(p, "exam_subject")}</b></div>
          </>
        )}
      </div>
      <p><strong>专业要求：</strong>{requirement}</p>
      <p><strong>匹配原因：</strong>{item.match_reason}</p>
      <p><strong>其他要求：</strong>{source === "civil" ? textValue(p, "other_requirement") : textValue(p, "other_requirement")}</p>
    </article>
  );
}

function PublicPositionPanel({ majorName }: { majorName: string }) {
  const [includeLow, setIncludeLow] = useState(false);
  const [activeTab, setActiveTab] = useState<"civil" | "military">("civil");
  const [result, setResult] = useState<PublicPositionResult | null>(null);
  const [status, setStatus] = useState("加载中...");

  useEffect(() => {
    let active = true;
    setStatus("加载中...");
    fetchPublicPositionsByMajor(majorName, includeLow, 80)
      .then((data) => {
        if (!active) return;
        setResult(data);
        setStatus("");
      })
      .catch((err) => {
        if (!active) return;
        setResult(null);
        setStatus(err instanceof Error ? err.message : "可报岗位加载失败");
      });
    return () => {
      active = false;
    };
  }, [majorName, includeLow]);

  if (status) return <div className="empty compact-empty">{status}</div>;
  if (!result) return null;

  const civil = result.civilService || [];
  const military = result.militaryCivilian || [];
  const rows = activeTab === "civil" ? civil : military;

  if (!result.civilServiceTotal && !result.militaryCivilianTotal) return null;

  return (
    <section className="drawer-section public-position-section">
      <div className="public-position-title">
        <div>
          <h3>可报公职岗位</h3>
          <p>匹配结果仅供初筛，最终以招录机关解释和公告条件为准。</p>
        </div>
        <label className="low-confidence-toggle">
          <input type="checkbox" checked={includeLow} onChange={(event) => setIncludeLow(event.target.checked)} />
          包含低可信
        </label>
      </div>
      <div className="public-position-tabs">
        <button type="button" className={activeTab === "civil" ? "active" : ""} onClick={() => setActiveTab("civil")}>
          河北公务员 {result.civilServiceTotal}
        </button>
        <button type="button" className={activeTab === "military" ? "active" : ""} onClick={() => setActiveTab("military")}>
          军队文职 {result.militaryCivilianTotal}
        </button>
      </div>
      <div className="public-position-list">
        {rows.map((item) => (
          <PublicPositionCard
            key={`${activeTab}-${textValue(item.position, "position_code")}-${item.match_type}`}
            item={item}
            source={activeTab}
          />
        ))}
        {!rows.length && <div className="empty compact-empty">当前筛选下暂无可展示岗位。</div>}
      </div>
    </section>
  );
}

export function SchoolDetailPanel({ schoolName, subject }: { schoolName: string; subject: Subject }) {
  const [detail, setDetail] = useState<SchoolDetail | null>(null);
  const [status, setStatus] = useState("加载中...");

  useEffect(() => {
    let active = true;
    setStatus("加载中...");
    fetchSchoolDetail(schoolName, subject)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setStatus(data ? "" : "暂无院校画像数据，请先执行最新 migration 并补充院校画像表。");
      })
      .catch((err) => {
        if (!active) return;
        setDetail(null);
        setStatus(err instanceof Error ? err.message : "院校画像加载失败");
      });
    return () => {
      active = false;
    };
  }, [schoolName, subject]);

  if (status) return <div className="empty compact-empty">{status}</div>;
  if (!detail?.profile) return <div className="empty compact-empty">暂无院校画像数据。</div>;

  const profile = detail.profile;
  const ranking = detail.rankings[0];

  return (
    <div className="profile-section">
      <div className="profile-hero">
        <div>
          <h3>{profile.school_name}</h3>
          <p>{profile.province || "-"} {profile.campus_city ?? profile.city ?? ""}</p>
        </div>
        <div className="tag-row">
          {profile.is_985 && <span className="tag">985</span>}
          {profile.is_211 && <span className="tag">211</span>}
          {profile.is_double_first_class && <span className="tag">双一流</span>}
          {profile.school_tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}
        </div>
      </div>

      <div className="detail-grid">
        <div><span>院校类型</span><b>{profile.school_type || "待补充"}</b></div>
        <div><span>办学性质</span><b>{profile.ownership || "待补充"}</b></div>
        <div><span>城市能级</span><b>{profile.city_tier || "待补充"}</b></div>
        <div><span>软科排名</span><b>{ranking ? `${ranking.ranking_year} 年 ${ranking.rank_label ?? ranking.rank_no ?? "-"}` : "待补充"}</b></div>
        <div><span>推免资格</span><b>{profile.has_postgrad_recommend == null ? "待补充" : profile.has_postgrad_recommend ? "有" : "无"}</b></div>
        <div><span>推免率</span><b>{profile.postgrad_recommend_rate == null ? "待补充" : `${profile.postgrad_recommend_rate}%`}</b></div>
      </div>

      <section className="drawer-section">
        <h3>双一流学科</h3>
        <p>{joinList(profile.double_first_class_subjects, "待补充")}</p>
      </section>
      <section className="drawer-section">
        <h3>推免去向</h3>
        <p>{joinList(profile.postgrad_destinations, "待补充")}</p>
      </section>
      <section className="drawer-section">
        <h3>学科评估</h3>
        {detail.disciplines.length ? (
          <div className="chip-list">
            {detail.disciplines.map((item) => (
              <span key={`${item.discipline_name}-${item.evaluation_round}`}>{item.discipline_name} {item.evaluation_grade}</span>
            ))}
          </div>
        ) : (
          <p>待补充教育部学科评估数据。</p>
        )}
      </section>
      <section className="drawer-section">
        <h3>历年投档趋势</h3>
        <div className="history-list">
          {detail.admissionTrend.map((item) => (
            <div key={item.year}>
              <b>{item.year}</b>
              <span>最低分 {item.min_score ?? "-"} / 最优位次 {formatNumber(item.best_rank)} / 专业 {item.major_count} 个</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function MajorDetailPanel({
  majorName,
  schoolName,
  subject,
}: {
  majorName: string;
  schoolName?: string;
  subject: Subject;
}) {
  const [detail, setDetail] = useState<MajorDetail | null>(null);
  const [status, setStatus] = useState("加载中...");

  useEffect(() => {
    let active = true;
    setStatus("加载中...");
    fetchMajorDetail(majorName, schoolName || "", subject)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setStatus(data ? "" : "暂无专业画像数据，请先执行最新 migration 并补充专业画像表。");
      })
      .catch((err) => {
        if (!active) return;
        setDetail(null);
        setStatus(err instanceof Error ? err.message : "专业画像加载失败");
      });
    return () => {
      active = false;
    };
  }, [majorName, schoolName, subject]);

  if (status) return <div className="empty compact-empty">{status}</div>;
  if (!detail?.profile) return <div className="empty compact-empty">暂无专业画像数据。</div>;

  const profile = detail.profile;
  const fallbackDirections = profile.job_directions.length
    ? profile.job_directions
    : ["行业通用岗位方向待补充", "可结合院校培养方案、就业报告和招考简章继续完善"];

  return (
    <div className="profile-section">
      <div className="profile-hero">
        <div>
          <h3>{profile.major_name}</h3>
          <p>{profile.discipline_category || "学科门类待补充"} / {profile.major_category || "专业类待补充"}</p>
        </div>
        <span className="tag">{profile.industry_outlook || "行业景气待补充"}</span>
      </div>

      <section className="drawer-section">
        <h3>专业描述</h3>
        <p>{profile.description || "该专业已在投档数据中出现，培养目标、课程体系和院校特色待继续补充。"}</p>
        {profile.knowledge_source_note && (
          <p className="drawer-note">知识库来源：专业知识库 / 可信度：{profile.knowledge_credibility || "待核实"}</p>
        )}
      </section>
      <section className="drawer-section">
        <h3>就业方向</h3>
        <div className="chip-list">{fallbackDirections.map((item) => <span key={item}>{item}</span>)}</div>
      </section>
      <section className="drawer-section">
        <h3>深造方向</h3>
        <p>{joinList(profile.further_study_directions, "待补充考研/保研方向。")}</p>
      </section>
      {detail.jobs.length > 0 && (
        <section className="drawer-section">
          <h3>就业样本与薪资</h3>
          <div className="job-card-list">
            {groupJobOffers(detail.jobs).map((group) => (
              <JobOfferGroupCard key={jobGroupKey(group[0])} records={group} />
            ))}
          </div>
        </section>
      )}
      <PublicPositionPanel majorName={majorName} />
      <section className="drawer-section">
        <h3>同专业不同院校对比</h3>
        <div className="mini-table">
          {detail.schoolCompare.map((item) => (
            <div key={`${item.school_code}-${item.major_name}`}>
              <strong>{item.school_name}</strong>
              <span>最优位次 {formatNumber(item.best_rank)} / 最宽位次 {formatNumber(item.worst_rank)} / {item.history_years} 年</span>
            </div>
          ))}
          {!detail.schoolCompare.length && <div className="empty compact-empty">暂无同专业对比数据。</div>}
        </div>
      </section>
    </div>
  );
}

export function JobsOverviewPanel() {
  const [filters, setFilters] = useState<JobOfferSearchFilters>({
    schoolQuery: "",
    majorQuery: "",
    degreeLevel: "all",
    dataYear: null,
    companyQuery: "",
    limit: 80,
    offset: 0,
  });
  const [submittedFilters, setSubmittedFilters] = useState<JobOfferSearchFilters>(filters);
  const [result, setResult] = useState<JobOfferSearchResult>({ total: 0, records: [] });
  const [status, setStatus] = useState("加载中...");

  useEffect(() => {
    let active = true;
    setStatus("加载中...");
    searchJobOffers(submittedFilters)
      .then((data) => {
        if (!active) return;
        setResult(data);
        setStatus("");
      })
      .catch((err) => {
        if (!active) return;
        setResult({ total: 0, records: [] });
        setStatus(err instanceof Error ? err.message : "就业数据加载失败");
      });
    return () => {
      active = false;
    };
  }, [submittedFilters]);

  const records = result.records || [];
  const page = Math.floor(submittedFilters.offset / submittedFilters.limit) + 1;
  const totalPages = Math.max(1, Math.ceil(result.total / submittedFilters.limit));
  const groupedRecords = groupJobOffers(records);

  function updateFilter<K extends keyof JobOfferSearchFilters>(key: K, value: JobOfferSearchFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function submitSearch() {
    setSubmittedFilters({ ...filters, offset: 0 });
  }

  function resetSearch() {
    const nextFilters: JobOfferSearchFilters = {
      schoolQuery: "",
      majorQuery: "",
      degreeLevel: "all",
      dataYear: null,
      companyQuery: "",
      limit: 80,
      offset: 0,
    };
    setFilters(nextFilters);
    setSubmittedFilters(nextFilters);
  }

  function changePage(direction: "prev" | "next") {
    const nextOffset =
      direction === "prev"
        ? Math.max(0, submittedFilters.offset - submittedFilters.limit)
        : submittedFilters.offset + submittedFilters.limit;
    if (nextOffset >= result.total && direction === "next") return;
    const nextFilters = { ...submittedFilters, offset: nextOffset };
    setSubmittedFilters(nextFilters);
    setFilters(nextFilters);
  }

  if (status) return <div className="empty">{status}</div>;

  return (
    <div className="jobs-page">
      <div className="panel-title">
        <div>
          <h2>就业数据</h2>
          <p className="muted">按学校、专业、学历层次、毕业年份和企业查询就业 offer 样本。</p>
        </div>
      </div>
      <div className="job-search-panel">
        <label>
          <span>学校</span>
          <input value={filters.schoolQuery} onChange={(event) => updateFilter("schoolQuery", event.target.value)} placeholder="例如：清华大学" />
        </label>
        <label>
          <span>专业</span>
          <input value={filters.majorQuery} onChange={(event) => updateFilter("majorQuery", event.target.value)} placeholder="例如：计算机、会计" />
        </label>
        <label>
          <span>学历层次</span>
          <select value={filters.degreeLevel} onChange={(event) => updateFilter("degreeLevel", event.target.value)}>
            <option value="all">全部</option>
            <option value="本科">本科</option>
            <option value="硕士">硕士</option>
            <option value="博士">博士</option>
          </select>
        </label>
        <label>
          <span>毕业年份</span>
          <select value={filters.dataYear ?? "all"} onChange={(event) => updateFilter("dataYear", event.target.value === "all" ? null : Number(event.target.value))}>
            <option value="all">全部</option>
            <option value="2024">2024</option>
            <option value="2025">2025</option>
            <option value="2026">2026</option>
          </select>
        </label>
        <label>
          <span>企业</span>
          <input value={filters.companyQuery} onChange={(event) => updateFilter("companyQuery", event.target.value)} placeholder="例如：华为、腾讯" />
        </label>
        <div className="job-search-actions">
          <button type="button" onClick={submitSearch}>查询</button>
          <button type="button" className="secondary" onClick={resetSearch}>重置</button>
        </div>
      </div>
      <section className="drawer-section">
        <div className="job-result-head">
          <h3>查询结果</h3>
          <span>共 {result.total.toLocaleString("zh-CN")} 条 offer，第 {page} / {totalPages} 页</span>
        </div>
        <div className="job-card-list">
          {groupedRecords.map((group) => (
            <JobOfferGroupCard key={jobGroupKey(group[0])} records={group} />
          ))}
          {!records.length && <div className="empty compact-empty">暂无匹配的就业 offer，请调整查询条件。</div>}
        </div>
        <div className="pager job-pager">
          <button type="button" onClick={() => changePage("prev")} disabled={submittedFilters.offset <= 0}>上一页</button>
          <button type="button" onClick={() => changePage("next")} disabled={submittedFilters.offset + submittedFilters.limit >= result.total}>下一页</button>
        </div>
      </section>
    </div>
  );
}
