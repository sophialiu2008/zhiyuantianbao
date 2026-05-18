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
  await client.query(fs.readFileSync("supabase/migrations/022_get_major_detail_strict_job_level.sql", "utf8"));

  const undergraduate = await client.query(
    "select public.get_major_detail($1,$2,$3,$4) as data",
    ["会计", "集美大学", "physics", "本科"],
  );
  const master = await client.query(
    "select public.get_major_detail($1,$2,$3,$4) as data",
    ["会计", "集美大学", "physics", "硕士"],
  );

  console.log(JSON.stringify({
    undergraduateJobs: undergraduate.rows[0].data.jobs?.length || 0,
    masterJobs: master.rows[0].data.jobs?.length || 0,
    masterFirstCompany: master.rows[0].data.jobs?.[0]?.company_name_standard || null,
  }, null, 2));

  await client.end();
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
