import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  fetchLatestVolunteerList,
  fetchLocationOptions,
  fetchRank,
  fetchRecommendations,
  fetchSchoolProfile,
  isSupabaseConfigured,
  loginOrRegisterAppUser,
  saveVolunteerList,
} from "./supabase";
import { JobsOverviewPanel, MajorDetailPanel, SchoolDetailPanel } from "./ProfileViews";
import type { AppUser, LocationOption, QueryState, RankRecord, Recommendation, RiskType, SchoolProfileRow, Subject } from "./types";
import "./styles.css";

const initialQuery: QueryState = {
  year: 2025,
  subject: "physics",
  score: 628,
  keyword: "",
  risk: "all",
  tag: "all",
  provinces: [],
  cities: [],
  page: 1,
  pageSize: 50,
};

const volunteerStorageKey = "hebei-gaokao-volunteers-v2";
const deviceStorageKey = "hebei-gaokao-device-id";
const appUserStorageKey = "hebei-gaokao-app-user-v1";
const maxCompareSchools = 4;

const riskLabels: Record<Exclude<RiskType, "all">, string> = {
  reach: "冲",
  match: "稳",
  safe: "保",
};

function formatNumber(value: number | null | undefined) {
  return value == null ? "-" : value.toLocaleString("zh-CN");
}

function riskClass(type: string) {
  return `risk ${type}`;
}

function csvEscape(value: unknown) {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function getDeviceId() {
  const saved = localStorage.getItem(deviceStorageKey);
  if (saved) return saved;
  const generated = crypto.randomUUID();
  localStorage.setItem(deviceStorageKey, generated);
  return generated;
}

function historyTrend(row: Recommendation) {
  const points = [2023, 2024, 2025]
    .map((year) => row.history?.find((item) => item.year === year))
    .filter((item): item is { year: number; min_score: number | null; min_rank: number | null } => Boolean(item?.min_rank));
  if (points.length < 2) return "历史数据不足，暂不判断趋势。";
  const first = points[0].min_rank ?? 0;
  const last = points[points.length - 1].min_rank ?? 0;
  if (last < first) return "近年录取位次整体前移，竞争可能变强。";
  if (last > first) return "近年录取位次整体后移，竞争压力可能下降。";
  return "近年录取位次整体较平稳。";
}

function profileTrend(row: SchoolProfileRow) {
  const points = [2023, 2024, 2025]
    .map((year) => row.history?.find((item) => item.year === year))
    .filter((item): item is { year: number; min_score: number | null; min_rank: number | null } => Boolean(item?.min_rank));
  if (points.length < 2) return "数据不足";
  const first = points[0].min_rank ?? 0;
  const last = points[points.length - 1].min_rank ?? 0;
  const diff = last - first;
  if (Math.abs(diff) <= 500) return "基本稳定";
  return diff < 0 ? "位次前移" : "位次后移";
}

interface ComparedSchool {
  name: string;
  rows: SchoolProfileRow[];
}

function LoginScreen({ onLogin }: { onLogin: (user: AppUser) => void }) {
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    const normalizedPhone = phone.replace(/\s+/g, "");
    if (!/^1[3-9]\d{9}$/.test(normalizedPhone)) {
      setError("请输入有效的11位手机号。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const user = await loginOrRegisterAppUser(normalizedPhone);
      localStorage.setItem(appUserStorageKey, JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-copy auth-copy-redesign">
          <div className="auth-brand-card">
            <span>河北高考志愿填报系统</span>
            <strong>志愿工作台</strong>
            <p>推荐、院校、专业、就业数据集中查看</p>
          </div>
          <span className="auth-kicker">河北高考志愿填报系统</span>
          <h1 id="auth-title">用手机号进入你的志愿工作台</h1>
          <p>首次使用会自动创建账号，后续可继续查看推荐结果、就业样本、院校对比和已保存的志愿表。</p>

          <div className="auth-proof-grid" aria-label="系统能力">
            <div>
              <strong>三年投档趋势</strong>
              <span>按分数、位次、城市和院校标签筛选</span>
            </div>
            <div>
              <strong>专业就业样本</strong>
              <span>展示同校同专业 offer 与薪资信息</span>
            </div>
            <div>
              <strong>志愿表云端保存</strong>
              <span>登录后可恢复自己的志愿清单</span>
            </div>
          </div>
        </div>
        <div className="auth-copy auth-copy-legacy" aria-hidden="true">
          <span className="auth-kicker">河北高考志愿填报工具</span>
          <h1>手机号注册 / 登录</h1>
          <p>输入手机号即可进入系统。首次使用会自动创建账号，暂不需要短信验证码。</p>
        </div>
        <form className="auth-form" onSubmit={submitLogin}>
          <div className="auth-form-head">
            <span>登录 / 注册</span>
            <strong>手机号直达</strong>
          </div>
          <label>
            手机号
            <input
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="例如：13800000000"
              aria-describedby="phone-helper"
            />
          </label>
          <p id="phone-helper" className="auth-helper">当前版本暂不发送验证码，请使用自己的常用手机号。</p>
          {error && <div className="error auth-error">{error}</div>}
          {!isSupabaseConfigured && (
            <div className="notice auth-error">
              数据库尚未配置，暂时无法注册登录。
            </div>
          )}
          <button disabled={loading || !isSupabaseConfigured} type="submit">
            {loading ? "正在进入..." : "进入系统"}
          </button>
          <p className="auth-footnote">进入即表示创建或登录账号，后续可升级为短信验证码登录。</p>
        </form>
      </section>
    </main>
  );
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<AppUser | null>(() => {
    try {
      const saved = localStorage.getItem(appUserStorageKey);
      return saved ? (JSON.parse(saved) as AppUser) : null;
    } catch {
      return null;
    }
  });
  const [query, setQuery] = useState<QueryState>(initialQuery);
  const [rank, setRank] = useState<RankRecord | null>(null);
  const [rows, setRows] = useState<Recommendation[]>([]);
  const [volunteers, setVolunteers] = useState<Recommendation[]>([]);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<Recommendation | null>(null);
  const [showDataNote, setShowDataNote] = useState(false);
  const [activeView, setActiveView] = useState<"recommendations" | "schools" | "jobs" | "volunteers">("recommendations");
  const [schoolMode, setSchoolMode] = useState<"history" | "compare">("history");
  const [selectedSchoolProfile, setSelectedSchoolProfile] = useState<string | null>(null);
  const [selectedMajorProfile, setSelectedMajorProfile] = useState<{ schoolName?: string; majorName: string } | null>(null);
  const [schoolQuery, setSchoolQuery] = useState("");
  const [schoolMajorFilter, setSchoolMajorFilter] = useState("");
  const [schoolProfileRows, setSchoolProfileRows] = useState<SchoolProfileRow[]>([]);
  const [schoolLoading, setSchoolLoading] = useState(false);
  const [schoolError, setSchoolError] = useState("");
  const [compareQuery, setCompareQuery] = useState("");
  const [compareMajorFilter, setCompareMajorFilter] = useState("");
  const [comparedSchools, setComparedSchools] = useState<ComparedSchool[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState("");
  const [loading, setLoading] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [error, setError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [cloudStatus, setCloudStatus] = useState("");

  const total = rows[0]?.total_count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / query.pageSize));
  const filteredSchoolProfileRows = useMemo(() => {
    const keyword = schoolMajorFilter.trim();
    if (!keyword) return schoolProfileRows;
    return schoolProfileRows.filter((row) => `${row.major_code} ${row.major_name}`.includes(keyword));
  }, [schoolMajorFilter, schoolProfileRows]);
  const schoolProfileHead = schoolProfileRows[0] ?? null;
  const filteredComparedSchools = useMemo(() => {
    const keyword = compareMajorFilter.trim();
    return comparedSchools.map((school) => ({
      ...school,
      rows: keyword ? school.rows.filter((row) => `${row.major_code} ${row.major_name}`.includes(keyword)) : school.rows,
    }));
  }, [compareMajorFilter, comparedSchools]);

  const selectedCities = useMemo(() => {
    const source = query.provinces.length
      ? locations.filter((item) => query.provinces.includes(item.province))
      : locations;
    return Array.from(new Set(source.flatMap((item) => item.cities))).sort((a, b) => a.localeCompare(b, "zh-CN"));
  }, [locations, query.provinces]);

  const stats = useMemo(() => {
    return volunteers.reduce(
      (acc, item) => {
        acc[item.risk_type] += 1;
        return acc;
      },
      { reach: 0, match: 0, safe: 0 },
    );
  }, [volunteers]);

  const volunteerInsights = useMemo(() => {
    if (!volunteers.length) return ["加入志愿后会显示结构分析。"];
    const totalCount = volunteers.length;
    const reachRatio = stats.reach / totalCount;
    const safeRatio = stats.safe / totalCount;
    const messages: string[] = [];

    if (totalCount < 20) messages.push("当前志愿数量偏少，建议先扩充候选范围，再做排序取舍。");
    if (reachRatio > 0.4) messages.push("冲的比例偏高，建议增加稳和保，降低整体滑档风险。");
    if (safeRatio < 0.2 && totalCount >= 10) messages.push("保的比例偏低，建议补充录取位次明显更稳的专业。");
    if (stats.match >= stats.reach && stats.match >= stats.safe && safeRatio >= 0.2) {
      messages.push("当前冲稳保结构较均衡，可以继续按学校偏好调整顺序。");
    }

    return messages.length ? messages : ["当前结构暂无明显问题。"];
  }, [stats.match, stats.reach, stats.safe, volunteers.length]);

  useEffect(() => {
    if (!isSupabaseConfigured || !currentUser) return;
    void fetchLocationOptions()
      .then(setLocations)
      .catch(() => setLocations([]));
  }, [currentUser]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(volunteerStorageKey);
      if (saved) setVolunteers(JSON.parse(saved) as Recommendation[]);
    } catch {
      setVolunteers([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(volunteerStorageKey, JSON.stringify(volunteers));
  }, [volunteers]);

  async function runSearch(nextQuery = query) {
    setLoading(true);
    setError("");
    try {
      const rankRecord = await fetchRank(nextQuery);
      setRank(rankRecord);
      if (!rankRecord) {
        setRows([]);
        setError("没有找到该分数对应位次。");
        return;
      }
      const recommendations = await fetchRecommendations(nextQuery, rankRecord.cumulative_rank);
      setRows(recommendations);
    } catch (err) {
      setRows([]);
      setRank(null);
      setError(err instanceof Error ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  }

  function updateQuery(partial: Partial<QueryState>) {
    setQuery((current) => ({ ...current, ...partial }));
  }

  function toggleValue(values: string[], value: string) {
    return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
  }

  function updateProvinces(provinces: string[]) {
    const allowedCities = new Set(
      locations.filter((item) => !provinces.length || provinces.includes(item.province)).flatMap((item) => item.cities),
    );
    setQuery((current) => ({
      ...current,
      provinces,
      cities: current.cities.filter((city) => allowedCities.has(city)),
      page: 1,
    }));
  }

  function toggleProvince(province: string) {
    updateProvinces(toggleValue(query.provinces, province));
  }

  function toggleCity(city: string) {
    setQuery((current) => ({ ...current, cities: toggleValue(current.cities, city), page: 1 }));
  }

  function applyRegionShortcut(region: "jingjinji" | "yangtze" | "pearl" | "chengyu") {
    const map = {
      jingjinji: ["北京", "天津", "河北"],
      yangtze: ["上海", "江苏", "浙江", "安徽"],
      pearl: ["广东"],
      chengyu: ["四川", "重庆"],
    };
    updateProvinces(map[region]);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = { ...query, page: 1 };
    setQuery(next);
    setActiveView("recommendations");
    void runSearch(next);
  }

  async function submitSchoolProfile(event: FormEvent) {
    event.preventDefault();
    if (!schoolQuery.trim()) return;
    setActiveView("schools");
    setSchoolMode("history");
    setSchoolLoading(true);
    setSchoolError("");
    try {
      const data = await fetchSchoolProfile(schoolQuery, query.subject);
      setSchoolProfileRows(data);
      if (!data.length) setSchoolError("没有找到该院校的投档历史。");
    } catch (err) {
      setSchoolProfileRows([]);
      setSchoolError(err instanceof Error ? err.message : "院校库查询失败");
    } finally {
      setSchoolLoading(false);
    }
  }

  async function addCompareSchool(event?: FormEvent, presetName?: string) {
    event?.preventDefault();
    const name = (presetName ?? compareQuery).trim();
    if (!name) return;
    if (comparedSchools.length >= maxCompareSchools) {
      setCompareError(`最多对比 ${maxCompareSchools} 所院校。`);
      return;
    }
    if (comparedSchools.some((item) => item.name === name)) {
      setCompareError("该院校已在对比列表中。");
      return;
    }

    setActiveView("schools");
    setSchoolMode("compare");
    setCompareLoading(true);
    setCompareError("");
    try {
      const data = await fetchSchoolProfile(name, query.subject);
      if (!data.length) {
        setCompareError("没有找到该院校的投档历史。");
        return;
      }
      setComparedSchools((current) => [...current, { name: data[0].school_name, rows: data }]);
      setCompareQuery("");
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : "院校对比查询失败");
    } finally {
      setCompareLoading(false);
    }
  }

  function removeCompareSchool(name: string) {
    setComparedSchools((current) => current.filter((item) => item.name !== name));
  }

  function changePage(direction: -1 | 1) {
    const nextPage = Math.min(totalPages, Math.max(1, query.page + direction));
    const next = { ...query, page: nextPage };
    setQuery(next);
    void runSearch(next);
  }

  function addVolunteer(row: Recommendation) {
    if (volunteers.length >= 96) return;
    if (volunteers.some((item) => item.id === row.id)) return;
    setVolunteers((current) => [...current, row]);
  }

  function removeVolunteer(id: number) {
    setVolunteers((current) => current.filter((item) => item.id !== id));
  }

  function moveVolunteer(index: number, direction: -1 | 1) {
    setVolunteers((current) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) return current;
      const copy = [...current];
      [copy[index], copy[nextIndex]] = [copy[nextIndex], copy[index]];
      return copy;
    });
  }

  function clearVolunteers() {
    setVolunteers([]);
    setCopyStatus("");
    setCloudStatus("");
  }

  function volunteerText() {
    const lines = [
      "河北高考志愿填报参考表",
      `生成时间：${new Date().toLocaleString("zh-CN")}`,
      `当前查询：${query.year} 年 / ${query.subject === "physics" ? "物理" : "历史"} / ${query.score} 分`,
      rank ? `当前位次：${formatNumber(rank.cumulative_rank)}` : "",
      "",
      "序号\t类型\t院校代码\t院校名称\t专业代码\t专业名称\t投档分\t投档位次\t位次差\t所在地",
      ...volunteers.map((item, index) => {
        const location = item.province && item.city ? `${item.province}${item.campus_city ?? item.city}` : "";
        return [
          index + 1,
          riskLabels[item.risk_type],
          item.school_code,
          item.school_name,
          item.major_code,
          item.major_name,
          item.min_score,
          item.min_rank,
          item.rank_diff,
          location,
        ].join("\t");
      }),
      "",
      "说明：推荐结果仅用于历史投档位次参考，最终填报以河北省教育考试院官方系统及高校招生章程为准。",
    ].filter(Boolean);
    return lines.join("\n");
  }

  function exportCsv() {
    const header = ["序号", "类型", "院校代码", "院校名称", "专业代码", "专业名称", "投档分", "投档位次", "位次差", "历史年数", "省份", "城市"];
    const body = volunteers.map((item, index) => [
      index + 1,
      riskLabels[item.risk_type],
      item.school_code,
      item.school_name,
      item.major_code,
      item.major_name,
      item.min_score,
      item.min_rank,
      item.rank_diff,
      item.history_years,
      item.province ?? "",
      item.campus_city ?? item.city ?? "",
    ]);
    const csv = [header, ...body].map((row) => row.map(csvEscape).join(",")).join("\r\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `河北高考志愿表_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportPdf() {
    const printWindow = window.open("", "_blank", "width=980,height=720");
    if (!printWindow) {
      setCopyStatus("浏览器拦截了打印窗口，请允许弹窗后重试。");
      window.setTimeout(() => setCopyStatus(""), 2400);
      return;
    }

    const subjectLabel = query.subject === "physics" ? "物理" : "历史";
    const generatedAt = new Date().toLocaleString("zh-CN");
    const rowsHtml = volunteers
      .map((item, index) => {
        const location = item.province && item.city ? `${item.province} ${item.campus_city ?? item.city}` : "-";
        return `
          <tr>
            <td>${index + 1}</td>
            <td>${riskLabels[item.risk_type]}</td>
            <td>${item.school_name}</td>
            <td>${item.major_code} ${item.major_name}</td>
            <td>${item.min_score ?? "-"}</td>
            <td>${formatNumber(item.min_rank)}</td>
            <td>${item.rank_diff > 0 ? "+" : ""}${formatNumber(item.rank_diff)}</td>
            <td>${location}</td>
          </tr>
        `;
      })
      .join("");
    const insightHtml = volunteerInsights.map((message) => `<li>${message}</li>`).join("");

    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>河北高考志愿表</title>
          <style>
            * { box-sizing: border-box; }
            body { margin: 0; padding: 28px; color: #111827; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; }
            h1 { margin: 0 0 8px; font-size: 24px; }
            h2 { margin: 22px 0 10px; font-size: 16px; }
            p { margin: 4px 0; color: #475467; font-size: 13px; }
            .meta { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 18px 0; }
            .meta div { padding: 10px; border: 1px solid #d9dee7; border-radius: 6px; background: #f8fafc; }
            .meta b { display: block; margin-top: 4px; font-size: 16px; }
            table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }
            th, td { padding: 8px; border: 1px solid #d9dee7; text-align: left; vertical-align: top; }
            th { background: #f2f4f7; }
            ol, ul { margin: 6px 0 0 20px; padding: 0; color: #344054; font-size: 13px; }
            .note { margin-top: 18px; padding-top: 10px; border-top: 1px solid #d9dee7; }
            @media print {
              body { padding: 18mm; }
              button { display: none; }
              table { page-break-inside: auto; }
              tr { page-break-inside: avoid; page-break-after: auto; }
            }
          </style>
        </head>
        <body>
          <h1>河北高考志愿填报参考表</h1>
          <p>生成时间：${generatedAt}</p>
          <p>说明：推荐结果仅用于历史投档位次参考，最终填报以河北省教育考试院官方系统及高校招生章程为准。</p>

          <div class="meta">
            <div><span>科目组合</span><b>${subjectLabel}</b></div>
            <div><span>高考分数</span><b>${query.score} 分</b></div>
            <div><span>当前位次</span><b>${rank ? `${formatNumber(rank.cumulative_rank)} 位` : "-"}</b></div>
            <div><span>志愿数量</span><b>${volunteers.length} / 96</b></div>
          </div>

          <div class="meta">
            <div><span>冲</span><b>${stats.reach}</b></div>
            <div><span>稳</span><b>${stats.match}</b></div>
            <div><span>保</span><b>${stats.safe}</b></div>
            <div><span>年份口径</span><b>${query.year}</b></div>
          </div>

          <h2>结构分析</h2>
          <ul>${insightHtml}</ul>

          <h2>志愿明细</h2>
          <table>
            <thead>
              <tr>
                <th>序号</th>
                <th>类型</th>
                <th>院校</th>
                <th>专业</th>
                <th>投档分</th>
                <th>投档位次</th>
                <th>位次差</th>
                <th>所在地</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml || '<tr><td colspan="8">尚未加入志愿。</td></tr>'}
            </tbody>
          </table>

          <p class="note">打印提示：在系统打印窗口中选择“另存为 PDF”即可生成 PDF 文件。</p>
          <script>
            window.addEventListener("load", () => {
              window.focus();
              window.print();
            });
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  }

  async function copyVolunteers() {
    try {
      await navigator.clipboard.writeText(volunteerText());
      setCopyStatus("已复制");
      window.setTimeout(() => setCopyStatus(""), 1800);
    } catch {
      setCopyStatus("复制失败");
      window.setTimeout(() => setCopyStatus(""), 1800);
    }
  }

  async function saveCloudVolunteers() {
    if (!isSupabaseConfigured || !currentUser) return;
    setCloudStatus("保存中...");
    try {
      const userId = currentUser.id;
      const saved = await saveVolunteerList(userId, volunteers);
      setCloudStatus(`已保存到云端：${new Date(saved.updated_at).toLocaleString("zh-CN")}`);
    } catch (err) {
      setCloudStatus(err instanceof Error ? `保存失败：${err.message}` : "保存失败");
    }
  }

  async function restoreCloudVolunteers() {
    if (!isSupabaseConfigured || !currentUser) return;
    setCloudStatus("读取中...");
    try {
      const userId = currentUser.id;
      const latest = await fetchLatestVolunteerList(userId);
      if (!latest) {
        setCloudStatus("云端暂无已保存志愿表。");
        return;
      }
      setVolunteers(latest.items || []);
      setCloudStatus(`已恢复云端版本：${new Date(latest.updated_at).toLocaleString("zh-CN")}`);
    } catch (err) {
      setCloudStatus(err instanceof Error ? `读取失败：${err.message}` : "读取失败");
    }
  }

  function logout() {
    localStorage.removeItem(appUserStorageKey);
    setCurrentUser(null);
  }

  function renderVolunteerPanelContent() {
    return (
      <>
        <div className="panel-title">
          <h2>志愿表</h2>
          <span className="muted">{volunteers.length} / 96</span>
        </div>
        <div className="stats">
          <div><b>{stats.reach}</b><span>冲</span></div>
          <div><b>{stats.match}</b><span>稳</span></div>
          <div><b>{stats.safe}</b><span>保</span></div>
        </div>
        <div className="volunteer-actions">
          <button type="button" disabled={!volunteers.length} onClick={exportCsv}>导出 CSV</button>
          <button type="button" disabled={!volunteers.length} onClick={exportPdf}>导出 PDF</button>
          <button type="button" disabled={!volunteers.length} onClick={copyVolunteers}>复制文本</button>
          <button type="button" disabled={!volunteers.length} onClick={clearVolunteers}>清空</button>
          <button type="button" disabled={!isSupabaseConfigured} onClick={saveCloudVolunteers}>云端保存</button>
          <button type="button" disabled={!isSupabaseConfigured} onClick={restoreCloudVolunteers}>云端恢复</button>
        </div>
        {copyStatus && <p className="copy-status">{copyStatus}</p>}
        {cloudStatus && <p className="copy-status">{cloudStatus}</p>}
        <div className="volunteer-insights">
          <strong>结构分析</strong>
          {volunteerInsights.map((message) => <p key={message}>{message}</p>)}
        </div>
        <div className="volunteer-list">
          {volunteers.map((item, index) => (
            <div className="volunteer-item" key={item.id}>
              <b>{index + 1}</b>
              <div>
                <span className={riskClass(item.risk_type)}>{riskLabels[item.risk_type]}</span>
                <strong>{item.school_name}</strong>
                <p>{item.major_code} {item.major_name}</p>
              </div>
              <div className="volunteer-item-actions">
                <button disabled={index === 0} onClick={() => moveVolunteer(index, -1)} type="button">↑</button>
                <button disabled={index === volunteers.length - 1} onClick={() => moveVolunteer(index, 1)} type="button">↓</button>
                <button className="remove" onClick={() => removeVolunteer(item.id)} type="button">删</button>
              </div>
            </div>
          ))}
          {!volunteers.length && <div className="empty">尚未加入志愿。</div>}
        </div>
      </>
    );
  }

  if (!currentUser) {
    return <LoginScreen onLogin={setCurrentUser} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>河北高考志愿填报工具</h1>
          <p>Supabase 数据库实时查询版，支持三年趋势、院校画像、专业画像、就业数据和本地志愿表。</p>
        </div>
        <div className="topbar-actions">
          <button className="secondary-button" type="button" onClick={() => setShowDataNote(true)}>
            数据说明
          </button>
          <span className={isSupabaseConfigured ? "status ready" : "status warn"}>
            {isSupabaseConfigured ? "数据库已连接" : "需要配置数据库"}
          </span>
          <div className="user-menu">
            <span>{currentUser.phone}</span>
            <button className="secondary-button" type="button" onClick={logout}>
              退出
            </button>
          </div>
        </div>
      </header>

      {!isSupabaseConfigured && (
        <section className="notice">
          <strong>需要配置 Supabase：</strong>
          复制 <code>frontend/.env.example</code> 为 <code>frontend/.env.local</code>，填写项目 URL 和 anon key。
          然后执行 <code>supabase/migrations/001_init_gaokao.sql</code> 与导入脚本。
        </section>
      )}

      <main className="layout">
        <section className="panel query-panel">
          <div className="panel-title">
            <h2>位次查询</h2>
            <span className="muted">每次只取一页推荐</span>
          </div>

          <form onSubmit={submit} className="form-grid">
            <label>
              年份
              <select value={query.year} onChange={(event) => updateQuery({ year: Number(event.target.value) })}>
                <option value={2025}>2025</option>
                <option value={2024}>2024</option>
                <option value={2023}>2023</option>
              </select>
            </label>

            <label>
              科目组合
              <select value={query.subject} onChange={(event) => updateQuery({ subject: event.target.value as Subject })}>
                <option value="physics">物理</option>
                <option value="history">历史</option>
              </select>
            </label>

            <label>
              高考分数
              <input
                type="number"
                min={140}
                max={750}
                value={query.score}
                onChange={(event) => updateQuery({ score: Number(event.target.value) })}
              />
            </label>

            <button disabled={loading || !isSupabaseConfigured} type="submit">
              {loading ? "查询中" : "生成推荐"}
            </button>
          </form>

          <div className="filters">
            <label>
              搜索学校/专业，支持逗号分隔
              <input
                value={query.keyword}
                onChange={(event) => updateQuery({ keyword: event.target.value })}
                placeholder="例如：统计学, 人工智能, 计算机"
              />
            </label>
            <button
              className="filter-toggle"
              type="button"
              onClick={() => setFiltersOpen((current) => !current)}
              aria-expanded={filtersOpen}
            >
              {filtersOpen ? "收起高级筛选" : "展开高级筛选"}
            </button>
            <div className={filtersOpen ? "advanced-filters open" : "advanced-filters"}>
              <label>
                推荐类型
                <select value={query.risk} onChange={(event) => updateQuery({ risk: event.target.value as RiskType })}>
                  <option value="all">全部</option>
                  <option value="reach">冲</option>
                  <option value="match">稳</option>
                  <option value="safe">保</option>
                </select>
              </label>
              <label>
                院校标签
                <select value={query.tag} onChange={(event) => updateQuery({ tag: event.target.value })}>
                  <option value="all">全部</option>
                  <option value="985">985</option>
                  <option value="211">211</option>
                  <option value="双一流">双一流</option>
                  <option value="普通本科">普通本科</option>
                </select>
              </label>

              <div className="multi-filter">
                <div className="filter-head">
                  <span>所在省份（可多选）</span>
                  <button type="button" className="link-button" onClick={() => updateProvinces([])}>
                    清空
                  </button>
                </div>
                <div className="shortcut-row">
                  <button type="button" onClick={() => applyRegionShortcut("jingjinji")}>京津冀</button>
                  <button type="button" onClick={() => applyRegionShortcut("yangtze")}>长三角</button>
                  <button type="button" onClick={() => applyRegionShortcut("pearl")}>珠三角</button>
                  <button type="button" onClick={() => applyRegionShortcut("chengyu")}>成渝</button>
                </div>
                <div className="check-grid province-grid">
                  {locations.map((item) => (
                    <label key={item.province} className="check-item">
                      <input
                        type="checkbox"
                        checked={query.provinces.includes(item.province)}
                        onChange={() => toggleProvince(item.province)}
                      />
                      {item.province}
                    </label>
                  ))}
                </div>
              </div>

              <div className="multi-filter">
                <div className="filter-head">
                  <span>所在城市（可多选）</span>
                  <button type="button" className="link-button" onClick={() => updateQuery({ cities: [], page: 1 })}>
                    清空
                  </button>
                </div>
                <div className="check-grid city-grid">
                  {selectedCities.slice(0, 80).map((city) => (
                    <label key={city} className="check-item">
                      <input type="checkbox" checked={query.cities.includes(city)} onChange={() => toggleCity(city)} />
                      {city}
                    </label>
                  ))}
                </div>
                <p className="hint">
                  {query.provinces.length ? "城市列表已按所选省份过滤。" : "未选省份时显示全部城市，建议先选省份。"}
                </p>
              </div>
            </div>
          </div>

          <div className="quick-actions">
            <div>
              <h3>快捷操作</h3>
              <p>左侧只负责输入，完整结果在右侧对应模块查看。</p>
            </div>

            <form className="quick-action-form" onSubmit={submitSchoolProfile}>
              <label>
                查询院校投档历史
                <input
                  value={schoolQuery}
                  onChange={(event) => setSchoolQuery(event.target.value)}
                  placeholder="例如：北京林业大学"
                />
              </label>
              <button disabled={schoolLoading || !isSupabaseConfigured || !schoolQuery.trim()} type="submit">
                {schoolLoading ? "查询中" : "查询"}
              </button>
            </form>

            <form className="quick-action-form" onSubmit={(event) => void addCompareSchool(event)}>
              <label>
                添加到院校对比
                <input
                  value={compareQuery}
                  onChange={(event) => setCompareQuery(event.target.value)}
                  placeholder="例如：中国人民大学"
                />
              </label>
              <button
                disabled={compareLoading || !isSupabaseConfigured || !compareQuery.trim() || comparedSchools.length >= maxCompareSchools}
                type="submit"
              >
                {compareLoading ? "添加中" : "添加"}
              </button>
            </form>

            <div className="compare-selection">
              <div className="filter-head">
                <span>已选对比院校</span>
                <span>{comparedSchools.length} / {maxCompareSchools}</span>
              </div>
              <div className="selected-school-list">
                {comparedSchools.map((school) => (
                  <button key={school.name} type="button" onClick={() => removeCompareSchool(school.name)}>
                    {school.name} ×
                  </button>
                ))}
                {!comparedSchools.length && <span className="hint">尚未添加院校。</span>}
              </div>
            </div>
          </div>
        </section>

        <section className="panel results-panel">
          <div className="view-tabs">
            <button
              className={activeView === "recommendations" ? "active" : ""}
              type="button"
              onClick={() => setActiveView("recommendations")}
            >
              推荐结果
            </button>
            <button
              className={activeView === "schools" ? "active" : ""}
              type="button"
              onClick={() => {
                setActiveView("schools");
                setSchoolMode("history");
              }}
            >
              院校
            </button>
            <button
              className={activeView === "jobs" ? "active" : ""}
              type="button"
              onClick={() => setActiveView("jobs")}
            >
              专业就业
            </button>
            <button
              className={activeView === "volunteers" ? "active" : ""}
              type="button"
              onClick={() => setActiveView("volunteers")}
            >
              志愿表
            </button>
          </div>

          {activeView === "recommendations" ? (
            <>
              <div className="panel-title">
                <h2>推荐结果</h2>
                <span className="muted">
                  {total ? `第 ${query.page} / ${totalPages} 页，共 ${formatNumber(total)} 条` : "暂无结果"}
                </span>
              </div>
              {error && <div className="error">{error}</div>}
              <div className="recommendation-cards">
                {rows.map((row) => {
                  const latest = row.history?.find((history) => history.year === 2025);
                  const location = row.province && row.city ? `${row.province} ${row.campus_city ?? row.city}` : "-";
                  return (
                    <article className="recommendation-card" key={row.id}>
                      <div className="recommendation-card-head">
                        <span className={riskClass(row.risk_type)}>{riskLabels[row.risk_type]}</span>
                        <span>{row.rank_diff > 0 ? "+" : ""}{formatNumber(row.rank_diff)} 位次差</span>
                      </div>
                      <button className="recommendation-school" type="button" onClick={() => setSelectedDetail(row)}>
                        {row.school_name}
                      </button>
                      <button
                        className="recommendation-major"
                        type="button"
                        onClick={() => setSelectedMajorProfile({ schoolName: row.school_name, majorName: row.major_name })}
                      >
                        {row.major_code} {row.major_name}
                      </button>
                      <div className="recommendation-meta">
                        <div><span>2025</span><b>{latest ? `${latest.min_score} 分` : "-"}</b><em>{latest ? `${formatNumber(latest.min_rank)} 位` : ""}</em></div>
                        <div><span>所在地</span><b>{location}</b></div>
                        <div><span>历史</span><b>{row.history_years} 年</b></div>
                      </div>
                      <div className="recommendation-actions">
                        <button type="button" onClick={() => addVolunteer(row)}>加入志愿</button>
                        <button className="secondary-button" type="button" onClick={() => setSelectedDetail(row)}>详情</button>
                        <button className="secondary-button" type="button" onClick={() => setSelectedSchoolProfile(row.school_name)}>院校</button>
                      </div>
                    </article>
                  );
                })}
                {!rows.length && !loading && <div className="empty">暂无结果。</div>}
              </div>
              <div className="table-wrap recommendation-table">
                <table>
                  <thead>
                    <tr>
                      <th>类型</th>
                      <th>学校 / 专业</th>
                      <th>2025</th>
                      <th>2024</th>
                      <th>2023</th>
                      <th>所在地</th>
                      <th>位次差</th>
                      <th>历史</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.id}>
                        <td>
                          <span className={riskClass(row.risk_type)}>{riskLabels[row.risk_type]}</span>
                        </td>
                        <td className="school-major">
                          <button className="text-link" type="button" onClick={() => setSelectedDetail(row)}>
                            {row.school_name}
                          </button>
                          <button className="inline-action" type="button" onClick={() => setSelectedSchoolProfile(row.school_name)}>
                            院校画像
                          </button>
                          {row.school_tags.map((tag) => (
                            <span key={tag} className="tag">{tag}</span>
                          ))}
                          <p>
                            {row.major_code}{" "}
                            <button
                              className="text-link muted-link"
                              type="button"
                              onClick={() => setSelectedMajorProfile({ schoolName: row.school_name, majorName: row.major_name })}
                            >
                              {row.major_name}
                            </button>
                          </p>
                        </td>
                        {[2025, 2024, 2023].map((year) => {
                          const item = row.history?.find((history) => history.year === year);
                          return (
                            <td key={year} className="year-cell">
                              {item ? (
                                <>
                                  <b>{item.min_score} 分</b>
                                  <span>{formatNumber(item.min_rank)} 位</span>
                                </>
                              ) : "-"}
                            </td>
                          );
                        })}
                        <td>{row.province && row.city ? `${row.province} ${row.campus_city ?? row.city}` : "-"}</td>
                        <td>{row.rank_diff > 0 ? "+" : ""}{formatNumber(row.rank_diff)}</td>
                        <td>{row.history_years} 年</td>
                        <td className="row-actions">
                          <button className="small" onClick={() => setSelectedDetail(row)} type="button">详情</button>
                          <button className="small" onClick={() => addVolunteer(row)} type="button">加入</button>
                        </td>
                      </tr>
                    ))}
                    {!rows.length && !loading && (
                      <tr>
                        <td colSpan={9} className="empty">暂无结果。</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="pager">
                <button disabled={query.page <= 1 || loading} onClick={() => changePage(-1)} type="button">上一页</button>
                <button disabled={query.page >= totalPages || loading || total === 0} onClick={() => changePage(1)} type="button">下一页</button>
              </div>
            </>
          ) : activeView === "volunteers" ? (
            <div className="volunteer-page">
              {renderVolunteerPanelContent()}
            </div>
          ) : activeView === "schools" ? (
            <>
              <div className="panel-title">
                <div>
                  <h2>院校</h2>
                  <p className="muted">集中查看院校投档历史、院校画像和多校对比。</p>
                </div>
                <span className="muted">
                  {schoolMode === "history" ? "投档历史" : `${comparedSchools.length} / ${maxCompareSchools}`}
                </span>
              </div>

              <div className="school-mode-tabs">
                <button
                  className={schoolMode === "history" ? "active" : ""}
                  type="button"
                  onClick={() => setSchoolMode("history")}
                >
                  投档历史
                </button>
                <button
                  className={schoolMode === "compare" ? "active" : ""}
                  type="button"
                  onClick={() => setSchoolMode("compare")}
                >
                  院校对比
                </button>
              </div>

              {schoolMode === "history" ? (
                <>
                  <div className="panel-title compact-title">
                    <div>
                      <h2>投档历史</h2>
                      <p className="muted">按院校查看近三年各专业投档分和位次。</p>
                    </div>
                    <span className="muted">
                      {filteredSchoolProfileRows.length ? `${filteredSchoolProfileRows.length} 个专业` : "暂无结果"}
                    </span>
                  </div>

                  {schoolProfileHead && (
                    <div className="school-summary">
                      <div>
                        <h3>{schoolProfileHead.school_name}</h3>
                        <p>
                          {schoolProfileHead.province && schoolProfileHead.city
                            ? `${schoolProfileHead.province} ${schoolProfileHead.campus_city ?? schoolProfileHead.city}`
                            : "-"}
                        </p>
                      </div>
                      <div>
                        {schoolProfileHead.school_tags.map((tag) => (
                          <span key={tag} className="tag">{tag}</span>
                        ))}
                      </div>
                      <button className="secondary-button" type="button" onClick={() => setSelectedSchoolProfile(schoolProfileHead.school_name)}>
                        院校画像
                      </button>
                      <button className="secondary-button" type="button" onClick={() => void addCompareSchool(undefined, schoolProfileHead.school_name)}>
                        加入对比
                      </button>
                    </div>
                  )}

                  <div className="school-profile-toolbar">
                    <label>
                      专业过滤
                      <input
                        value={schoolMajorFilter}
                        onChange={(event) => setSchoolMajorFilter(event.target.value)}
                        placeholder="例如：计算机、人工智能、临床医学"
                      />
                    </label>
                  </div>

                  {schoolError && <div className="error">{schoolError}</div>}
                  <div className="table-wrap">
                    <table className="school-profile-table">
                      <thead>
                        <tr>
                          <th>专业代码</th>
                          <th>专业名称</th>
                          <th>2025</th>
                          <th>2024</th>
                          <th>2023</th>
                          <th>趋势</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredSchoolProfileRows.map((row) => (
                          <tr key={`${row.school_name}-${row.major_name}`}>
                            <td>{row.major_code}</td>
                            <td className="school-major">
                              <button
                                className="text-link"
                                type="button"
                                onClick={() => setSelectedMajorProfile({ schoolName: row.school_name, majorName: row.major_name })}
                              >
                                {row.major_name}
                              </button>
                            </td>
                            {[2025, 2024, 2023].map((year) => {
                              const item = row.history?.find((history) => history.year === year);
                              return (
                                <td key={year} className="year-cell">
                                  {item ? (
                                    <>
                                      <b>{item.min_score} 分</b>
                                      <span>{formatNumber(item.min_rank)} 位</span>
                                    </>
                                  ) : "-"}
                                </td>
                              );
                            })}
                            <td>{profileTrend(row)}</td>
                          </tr>
                        ))}
                        {!filteredSchoolProfileRows.length && !schoolLoading && (
                          <tr>
                            <td colSpan={6} className="empty">输入院校名称后查看投档历史。</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <>
                  <div className="panel-title compact-title">
                    <div>
                      <h2>院校对比</h2>
                      <p className="muted">当前科目：{query.subject === "physics" ? "物理" : "历史"}，建议输入同一专业关键词进行比较。</p>
                    </div>
                    <span className="muted">{comparedSchools.length} / {maxCompareSchools}</span>
                  </div>

                  {compareError && <div className="error">{compareError}</div>}

                  <div className="compare-toolbar">
                    <label>
                      专业关键词
                      <input
                        value={compareMajorFilter}
                        onChange={(event) => setCompareMajorFilter(event.target.value)}
                        placeholder="例如：计算机、法学、临床医学"
                      />
                    </label>
                  </div>

                  <div className="compare-school-grid">
                    {comparedSchools.map((school) => {
                      const head = school.rows[0];
                      const best2025 = school.rows
                        .filter((row) => row.latest_year === 2025 && row.latest_rank)
                        .sort((a, b) => a.latest_rank - b.latest_rank)[0];
                      return (
                        <div className="compare-school-card" key={school.name}>
                          <div>
                            <h3>{school.name}</h3>
                            <p>{head?.province && head.city ? `${head.province} ${head.campus_city ?? head.city}` : "-"}</p>
                          </div>
                          <div className="compare-card-meta">
                            <span>{school.rows.length} 个专业</span>
                            <span>2025最高：{best2025 ? `${best2025.latest_score} 分 / ${formatNumber(best2025.latest_rank)} 位` : "-"}</span>
                          </div>
                          <button className="remove" type="button" onClick={() => removeCompareSchool(school.name)}>移除</button>
                        </div>
                      );
                    })}
                    {!comparedSchools.length && <div className="empty">请先在左侧添加院校。</div>}
                  </div>

                  <div className="table-wrap">
                    <table className="compare-table">
                      <thead>
                        <tr>
                          <th>院校</th>
                          <th>专业</th>
                          <th>2025</th>
                          <th>2024</th>
                          <th>2023</th>
                          <th>趋势</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredComparedSchools.flatMap((school) =>
                          school.rows.map((row) => (
                            <tr key={`${school.name}-${row.major_name}`}>
                              <td><strong>{school.name}</strong></td>
                              <td className="school-major">{row.major_code} {row.major_name}</td>
                              {[2025, 2024, 2023].map((year) => {
                                const item = row.history?.find((history) => history.year === year);
                                return (
                                  <td key={year} className="year-cell">
                                    {item ? (
                                      <>
                                        <b>{item.min_score} 分</b>
                                        <span>{formatNumber(item.min_rank)} 位</span>
                                      </>
                                    ) : "-"}
                                  </td>
                                );
                              })}
                              <td>{profileTrend(row)}</td>
                            </tr>
                          ))
                        )}
                        {comparedSchools.length > 0 && filteredComparedSchools.every((school) => school.rows.length === 0) && (
                          <tr>
                            <td colSpan={6} className="empty">当前专业关键词下暂无可对比记录。</td>
                          </tr>
                        )}
                        {!comparedSchools.length && (
                          <tr>
                            <td colSpan={6} className="empty">添加院校后显示对比结果。</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          ) : activeView === "jobs" ? (
            <JobsOverviewPanel />
          ) : null}
        </section>

        <aside className="panel volunteer-panel">
          {renderVolunteerPanelContent()}
        </aside>
      </main>

      <nav className="mobile-bottom-nav" aria-label="手机主导航">
        <button
          className={activeView === "recommendations" ? "active" : ""}
          type="button"
          onClick={() => setActiveView("recommendations")}
        >
          推荐
        </button>
        <button
          className={activeView === "schools" ? "active" : ""}
          type="button"
          onClick={() => {
            setActiveView("schools");
            setSchoolMode("history");
          }}
        >
          院校
        </button>
        <button
          className={activeView === "jobs" ? "active" : ""}
          type="button"
          onClick={() => setActiveView("jobs")}
        >
          专业
        </button>
        <button
          className={activeView === "volunteers" ? "active" : ""}
          type="button"
          onClick={() => setActiveView("volunteers")}
        >
          志愿
        </button>
      </nav>

      {selectedDetail && (
        <div className="drawer-backdrop" onClick={() => setSelectedDetail(null)}>
          <aside className="detail-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className={riskClass(selectedDetail.risk_type)}>{riskLabels[selectedDetail.risk_type]}</span>
                <h2>{selectedDetail.school_name}</h2>
                <p>{selectedDetail.major_code} {selectedDetail.major_name}</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setSelectedDetail(null)}>×</button>
            </div>

            <div className="detail-grid">
              <div><span>院校代码</span><b>{selectedDetail.school_code}</b></div>
              <div><span>所在地</span><b>{selectedDetail.province && selectedDetail.city ? `${selectedDetail.province} ${selectedDetail.campus_city ?? selectedDetail.city}` : "-"}</b></div>
              <div><span>位次差</span><b>{selectedDetail.rank_diff > 0 ? "+" : ""}{formatNumber(selectedDetail.rank_diff)}</b></div>
              <div><span>历史年数</span><b>{selectedDetail.history_years} 年</b></div>
            </div>

            <section className="drawer-section">
              <h3>近三年投档趋势</h3>
              <div className="history-list">
                {[2025, 2024, 2023].map((year) => {
                  const item = selectedDetail.history?.find((history) => history.year === year);
                  return (
                    <div key={year}>
                      <b>{year}</b>
                      <span>{item ? `${item.min_score} 分 / ${formatNumber(item.min_rank)} 位` : "无数据"}</span>
                    </div>
                  );
                })}
              </div>
              <p className="drawer-note">{historyTrend(selectedDetail)}</p>
            </section>

            <section className="drawer-section">
              <h3>参考口径</h3>
              <p>当前推荐按历史投档位次粗分为冲、稳、保，不预测当年最终录取结果。</p>
              <p>同一院校不同校区按实际就读城市标注，威海校区对应威海市。</p>
            </section>

            <div className="drawer-actions">
              <button type="button" onClick={() => addVolunteer(selectedDetail)}>加入志愿表</button>
              <button className="secondary-button" type="button" onClick={() => setSelectedSchoolProfile(selectedDetail.school_name)}>
                查看院校画像
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSelectedMajorProfile({ schoolName: selectedDetail.school_name, majorName: selectedDetail.major_name })}
              >
                查看专业详情
              </button>
            </div>
          </aside>
        </div>
      )}

      {selectedSchoolProfile && (
        <div className="drawer-backdrop" onClick={() => setSelectedSchoolProfile(null)}>
          <aside className="detail-drawer wide-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <h2>院校详情</h2>
                <p>{selectedSchoolProfile}</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setSelectedSchoolProfile(null)}>×</button>
            </div>
            <SchoolDetailPanel schoolName={selectedSchoolProfile} subject={query.subject} />
          </aside>
        </div>
      )}

      {selectedMajorProfile && (
        <div className="drawer-backdrop" onClick={() => setSelectedMajorProfile(null)}>
          <aside className="detail-drawer wide-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <h2>专业详情</h2>
                <p>{selectedMajorProfile.schoolName ? `${selectedMajorProfile.schoolName} · ` : ""}{selectedMajorProfile.majorName}</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setSelectedMajorProfile(null)}>×</button>
            </div>
            <MajorDetailPanel
              majorName={selectedMajorProfile.majorName}
              schoolName={selectedMajorProfile.schoolName}
              subject={query.subject}
            />
          </aside>
        </div>
      )}

      {showDataNote && (
        <div className="drawer-backdrop" onClick={() => setShowDataNote(false)}>
          <aside className="detail-drawer data-note" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <h2>数据说明</h2>
                <p>当前版本的数据来源、处理口径和使用边界</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setShowDataNote(false)}>×</button>
            </div>
            <section className="drawer-section">
              <h3>数据底座</h3>
              <p>投档数据来自 2023-2025 年河北本科批平行志愿投档统计表，位次数据来自对应年份一分一档表。</p>
              <p>清洗脚本输出 `rank_2023/2024/2025` 和 `admission_2023/2024/2025`，并生成行数、空值、重复、异常分数、异常位次、物理/历史数量校验报告。</p>
            </section>
            <section className="drawer-section">
              <h3>推荐逻辑</h3>
              <p>先用分数换算当年位次，再用同科目历史投档位次计算位次差，并按阈值划分冲、稳、保。</p>
              <p>推荐结果只基于历史投档位次，不包含招生计划变化、选科限制变化、专业组调整、考生偏好变化等因素。</p>
            </section>
            <section className="drawer-section">
              <h3>使用边界</h3>
              <p>本工具适合做候选范围筛选和志愿表初稿整理，最终填报必须以河北省教育考试院官方系统及高校招生章程为准。</p>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}
