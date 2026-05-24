const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.argv[2] || process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("Usage: node scripts/supabase_import/check_recommend_risk_distribution.cjs <database-url>");
  process.exit(1);
}

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  try {
    const rank = await client.query(
      "select * from public.get_rank_record($1, $2, $3)",
      [2025, "physics", 680],
    );
    const userRank = rank.rows[0]?.cumulative_rank;
    const risks = ["reach", "match", "safe"];
    const distribution = [];
    for (const risk of risks) {
      const result = await client.query(
        `select risk_type, count(*)::int as count, min(rank_diff) as min_diff, max(rank_diff) as max_diff
         from public.recommend_admissions($1,$2,$3,'',$4,'all',100,0,'{}'::text[],'{}'::text[])
         group by risk_type`,
        [2025, "physics", userRank, risk],
      );
      distribution.push(result.rows[0] || { risk_type: risk, count: 0, min_diff: null, max_diff: null });
    }
    console.log(JSON.stringify({ userRank, distribution }, null, 2));
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
