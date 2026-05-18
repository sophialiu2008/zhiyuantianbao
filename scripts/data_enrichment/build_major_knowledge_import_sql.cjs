const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourceFile = path.join(root, "data", "enriched", "public_positions", "major_profiles_for_matching.json");
const outDir = path.join(root, "data", "enriched", "major_knowledge");
const outFile = path.join(outDir, "major_knowledge_import.sql");
const summaryFile = path.join(outDir, "major_knowledge_summary.json");

function normalizeMajorName(name) {
  return String(name || "")
    .replace(/[（(].*?[）)]/g, "")
    .replace(/\s+/g, "")
    .trim();
}

function cleanName(name) {
  return String(name || "").replace(/\s+/g, "").trim();
}

function sqlString(value) {
  if (value == null) return "null";
  return `E'${String(value).replace(/\\/g, "\\\\").replace(/'/g, "''")}'`;
}

function sqlArray(values) {
  const cleaned = [...new Set((values || []).map((v) => String(v || "").trim()).filter(Boolean))];
  if (!cleaned.length) return "'{}'::text[]";
  return `array[${cleaned.map(sqlString).join(", ")}]::text[]`;
}

const templates = [
  {
    name: "计算机与数字技术",
    test: /(计算机|软件|人工智能|数据科学|大数据|网络工程|信息安全|物联网|智能科学|数字媒体技术|区块链|密码科学)/,
    discipline: "工学",
    majorCategory: "计算机类",
    job: ["软件开发", "算法与人工智能", "数据分析与数据工程", "网络安全", "系统运维与云计算", "产品与技术支持"],
    further: ["计算机科学与技术", "软件工程", "人工智能", "网络空间安全", "电子信息", "数据科学与大数据技术"],
    courses: ["程序设计", "数据结构", "计算机组成原理", "操作系统", "数据库系统", "计算机网络"],
  },
  {
    name: "电子信息与自动化",
    test: /(电子|通信|微电子|集成电路|光电|自动化|机器人工程|测控|智能装备|智能制造)/,
    discipline: "工学",
    majorCategory: "电子信息/自动化类",
    job: ["硬件研发", "嵌入式开发", "通信网络", "测试与质量工程", "自动化控制", "智能制造工程"],
    further: ["电子科学与技术", "信息与通信工程", "控制科学与工程", "电子信息", "集成电路工程"],
    courses: ["电路分析", "模拟电子技术", "数字电子技术", "信号与系统", "自动控制原理", "嵌入式系统"],
  },
  {
    name: "机械电气与能源",
    test: /(机械|车辆|电气|能源|动力|新能源|储能|工业工程|过程装备|飞行器|航空航天|船舶|兵器)/,
    discipline: "工学",
    majorCategory: "机械/电气/能源类",
    job: ["设备研发与设计", "生产工艺", "电力系统", "新能源工程", "质量管理", "项目实施与运维"],
    further: ["机械工程", "电气工程", "动力工程及工程热物理", "能源动力", "控制工程"],
    courses: ["工程制图", "理论力学", "机械设计", "电路基础", "电机学", "工程材料"],
  },
  {
    name: "土木建筑与交通",
    test: /(土木|建筑|城乡规划|风景园林|工程管理|工程造价|交通|道路|桥梁|水利|测绘|地理空间)/,
    discipline: "工学",
    majorCategory: "土木建筑/交通类",
    job: ["工程设计", "施工管理", "造价咨询", "项目管理", "规划设计", "交通运输组织"],
    further: ["土木工程", "建筑学", "城乡规划学", "交通运输工程", "工程管理"],
    courses: ["工程力学", "结构力学", "土木工程材料", "工程测量", "施工组织", "工程经济"],
  },
  {
    name: "化工材料与环境",
    test: /(化学|化工|材料|高分子|环境|安全工程|矿业|冶金|轻化|纺织|包装|印刷)/,
    discipline: "工学/理学",
    majorCategory: "化工材料/环境类",
    job: ["工艺研发", "质量检测", "材料研发", "环保工程", "安全评价", "生产技术管理"],
    further: ["化学工程与技术", "材料科学与工程", "环境科学与工程", "资源与环境", "材料与化工"],
    courses: ["无机化学", "有机化学", "物理化学", "化工原理", "材料科学基础", "环境监测"],
  },
  {
    name: "医学与药学",
    test: /(临床医学|口腔|中医|中西医|医学|护理|药学|麻醉|影像|检验|康复|公共卫生|预防|针灸|儿科|精神医学|眼视光)/,
    discipline: "医学",
    majorCategory: "医学类",
    job: ["临床诊疗", "医学检验", "医学影像", "药品研发与注册", "护理与康复", "公共卫生服务"],
    further: ["临床医学", "基础医学", "公共卫生与预防医学", "药学", "护理学", "中医学"],
    courses: ["人体解剖学", "生理学", "病理学", "药理学", "诊断学", "临床综合课程"],
  },
  {
    name: "财经管理",
    test: /(会计|财务|审计|金融|经济|财政|税收|保险|投资|工商管理|市场营销|人力资源|物流|电子商务|国际商务|贸易|管理科学)/,
    discipline: "经济学/管理学",
    majorCategory: "财经管理类",
    job: ["财务会计", "审计风控", "金融业务", "经营分析", "市场运营", "供应链与项目管理"],
    further: ["应用经济学", "工商管理", "会计", "金融", "审计", "管理科学与工程"],
    courses: ["微观经济学", "宏观经济学", "管理学", "会计学", "财务管理", "统计学"],
  },
  {
    name: "法学与公共治理",
    test: /(法学|知识产权|政治学|行政管理|公共事业|公共管理|社会工作|公安|侦查|治安|马克思主义|国际政治)/,
    discipline: "法学/管理学",
    majorCategory: "法学与公共管理类",
    job: ["法律事务", "合规风控", "公务员与事业单位", "公共管理", "基层治理", "企业法务"],
    further: ["法学", "法律硕士", "政治学", "公共管理", "社会学", "马克思主义理论"],
    courses: ["法理学", "宪法学", "民法学", "刑法学", "行政法", "诉讼法"],
  },
  {
    name: "教育语言与传媒",
    test: /(教育|学前|小学教育|汉语言|外国语|英语|日语|俄语|翻译|新闻|传播|广告|编辑|广播电视|网络与新媒体|历史|哲学)/,
    discipline: "教育学/文学/历史学/哲学",
    majorCategory: "教育语言传媒类",
    job: ["中小学教育", "内容编辑", "新媒体运营", "翻译与涉外服务", "文化传播", "培训与课程研发"],
    further: ["教育学", "中国语言文学", "外国语言文学", "新闻传播学", "历史学", "哲学"],
    courses: ["教育学", "心理学", "语言学概论", "文学史", "写作", "传播学概论"],
  },
  {
    name: "数学物理与基础科学",
    test: /(数学|统计|物理|应用物理|化学|生物科学|生态|地理科学|地球物理|天文|心理学|信息与计算科学)/,
    discipline: "理学",
    majorCategory: "基础科学类",
    job: ["数据分析", "科研助理", "教育培训", "模型建模", "质量检测", "技术支持"],
    further: ["数学", "统计学", "物理学", "化学", "生物学", "地理学"],
    courses: ["高等数学", "线性代数", "概率统计", "专业实验", "数理方法", "科研训练"],
  },
  {
    name: "农林食品与生命健康",
    test: /(农学|植物|动物|兽医|林学|园艺|园林|水产|食品|生物工程|生物技术|茶学|草业)/,
    discipline: "农学/工学/理学",
    majorCategory: "农林食品与生命健康类",
    job: ["农业技术服务", "食品研发与检测", "动植物生产管理", "生物技术研发", "质量监管", "乡村产业运营"],
    further: ["作物学", "园艺学", "畜牧学", "兽医学", "食品科学与工程", "生物学"],
    courses: ["生物化学", "遗传学", "微生物学", "食品化学", "植物生理学", "动物生理学"],
  },
  {
    name: "艺术体育",
    test: /(艺术|设计|美术|音乐|舞蹈|戏剧|影视|动画|播音|表演|体育|运动训练|社会体育)/,
    discipline: "艺术学/教育学",
    majorCategory: "艺术体育类",
    job: ["视觉设计", "内容创作", "文化艺术机构", "体育教育与训练", "品牌传播", "赛事与活动运营"],
    further: ["艺术学", "设计学", "音乐与舞蹈学", "戏剧与影视学", "体育学"],
    courses: ["艺术概论", "设计基础", "专业创作", "传播策划", "运动生理学", "训练学"],
  },
];

const fallback = {
  name: "通用专业",
  discipline: null,
  majorCategory: "综合类",
  job: ["专业技术岗位", "运营与项目支持", "数据与信息整理", "公务员与事业单位", "企业综合管理"],
  further: ["本专业相关一级学科", "专业硕士方向", "交叉学科方向", "公共管理或工商管理方向"],
  courses: ["专业基础课程", "专业核心课程", "实践实训", "毕业论文或综合设计"],
};

function pickTemplate(name) {
  return templates.find((template) => template.test.test(name)) || fallback;
}

function buildDescription(majorName, template) {
  return `${majorName}主要围绕${template.majorCategory || template.name}领域的基础理论、专业方法和实践能力展开培养，强调专业基础、应用训练与真实问题解决能力。学生通常需要掌握该领域的核心知识体系，并结合数据分析、项目实践、沟通协作等能力，面向升学深造、企业岗位、事业单位及公职岗位等多种路径发展。`;
}

function buildRecords() {
  const raw = JSON.parse(fs.readFileSync(sourceFile, "utf8"));
  const map = new Map();
  for (const row of raw) {
    const majorName = cleanName(row.major_name);
    const normalized = normalizeMajorName(majorName);
    if (!majorName || !normalized) continue;
    const existing = map.get(normalized);
    if (!existing || majorName.length < existing.majorName.length) {
      map.set(normalized, { majorName, normalized });
    }
  }
  return [...map.values()].sort((a, b) => a.normalized.localeCompare(b.normalized, "zh-CN"));
}

function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const records = buildRecords();
  const rows = records.map((record) => {
    const template = pickTemplate(record.normalized);
    const description = buildDescription(record.majorName, template);
    return [
      sqlString(record.majorName),
      sqlString(record.normalized),
      sqlString(template.discipline),
      sqlString(template.majorCategory),
      sqlString(description),
      sqlArray(template.job),
      sqlArray(template.further),
      sqlArray(template.courses),
      sqlString("由本地投档专业库按专业名称规则生成，作为专业详情兜底知识；后续可用教育部专业目录、阳光高考和学院官网资料逐条校准。"),
      sqlString("中"),
    ].join(", ");
  });

  const sql = `truncate table public.major_knowledge_base;\n\ninsert into public.major_knowledge_base (\n  major_name,\n  major_name_normalized,\n  discipline_category,\n  major_category,\n  description,\n  job_directions,\n  further_study_directions,\n  core_courses,\n  source_note,\n  credibility\n)\nvalues\n${rows.map((row) => `  (${row})`).join(",\n")}\non conflict (major_name_normalized) do update set\n  major_name = excluded.major_name,\n  discipline_category = excluded.discipline_category,\n  major_category = excluded.major_category,\n  description = excluded.description,\n  job_directions = excluded.job_directions,\n  further_study_directions = excluded.further_study_directions,\n  core_courses = excluded.core_courses,\n  source_note = excluded.source_note,\n  credibility = excluded.credibility,\n  updated_at = now();\n\nselect count(*) as imported_major_knowledge_rows from public.major_knowledge_base;\n`;

  fs.writeFileSync(outFile, sql, "utf8");
  const categoryCounts = {};
  for (const record of records) {
    const category = pickTemplate(record.normalized).majorCategory || "未分类";
    categoryCounts[category] = (categoryCounts[category] || 0) + 1;
  }
  fs.writeFileSync(
    summaryFile,
    JSON.stringify({ recordCount: records.length, categoryCounts }, null, 2),
    "utf8",
  );
  console.log(`Wrote ${records.length} rows to ${path.relative(root, outFile)}`);
}

main();
