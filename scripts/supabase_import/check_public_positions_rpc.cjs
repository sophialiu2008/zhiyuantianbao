const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("DATABASE_URL is required.");
  process.exit(1);
}

const majors = process.argv.slice(2);
const queries = majors.length ? majors : ["计算机", "会计", "法学"];

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  try {
    for (const major of queries) {
      const result = await client.query(
        "select public.search_public_positions_by_major($1,$2,$3) as data",
        [major, false, 5],
      );
      const data = result.rows[0].data;
      const firstCivil = data.civilService?.[0]?.position?.position_name || "-";
      const firstMilitary = data.militaryCivilian?.[0]?.position?.position_name || "-";
      console.log(
        `${major}: civil=${data.civilServiceTotal}, military=${data.militaryCivilianTotal}, firstCivil=${firstCivil}, firstMilitary=${firstMilitary}`,
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
