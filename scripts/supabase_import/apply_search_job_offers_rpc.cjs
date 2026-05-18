const fs = require("fs");
const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.argv[2] || process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("Missing database URL.");
  process.exit(1);
}

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  await client.query(fs.readFileSync("supabase/migrations/021_search_job_offers_rpc.sql", "utf8"));
  const result = await client.query(
    "select public.search_job_offers($1,$2,$3,$4,$5,$6,$7) as data",
    ["集美大学", "会计", "all", null, "", 8, 0],
  );
  console.log(JSON.stringify(result.rows[0].data, null, 2).slice(0, 1200));
  await client.end();
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
