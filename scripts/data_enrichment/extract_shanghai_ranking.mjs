import fs from "node:fs";
import vm from "node:vm";

const input = process.argv[2] || "data/external/school_sources/shanghairanking_2025_payload.decoded.js";
const output = process.argv[3] || "data/external/school_sources/shanghairanking_2025.json";
const source = fs.readFileSync(input, "utf8");
let captured = null;
const context = {
  __NUXT_JSONP__: (path, payload) => {
    captured = { path, payload };
  },
};

vm.createContext(context);
vm.runInContext(source, context, { timeout: 5000 });

const universities = captured?.payload?.data?.[0]?.univData || [];
const rows = universities.map((item) => ({
  school_name: item.univNameCn,
  school_name_en: item.univNameEn,
  province: item.province,
  school_type: item.univCategory,
  tags: item.univTags || [],
  ranking_year: 2025,
  ranking_name: "软科中国大学排名",
  rank_no: Number.parseInt(item.rankOverall || item.ranking, 10) || null,
  rank_label: item.rankOverall || item.ranking || "",
  score: item.score ?? null,
}));

fs.writeFileSync(output, JSON.stringify(rows, null, 2), "utf8");
console.log(`Extracted ${rows.length} ShanghaiRanking rows -> ${output}`);
