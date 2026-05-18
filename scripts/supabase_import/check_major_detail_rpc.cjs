const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.env.DATABASE_URL;
const majors = process.argv.slice(2);

if (!databaseUrl) {
  console.error("DATABASE_URL is required.");
  process.exit(1);
}

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  try {
    for (const major of majors.length ? majors : ["计算机", "会计", "法学"]) {
      const result = await client.query(
        "select public.get_major_detail($1,$2,$3,$4) as data",
        [major, "", "physics", "本科"],
      );
      const data = result.rows[0].data;
      const profile = data?.profile || {};
      console.log(
        `${major}: matched=${profile.major_name || "-"}, category=${profile.major_category || "-"}, desc=${String(profile.description || "").slice(0, 34)}, jobs=${(profile.job_directions || []).join("/")}, further=${(profile.further_study_directions || []).join("/")}`,
      );
    }
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
