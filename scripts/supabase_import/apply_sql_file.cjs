const fs = require("fs");
const path = require("path");
const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.argv[2] || process.env.DATABASE_URL;
const fileArg = process.argv[3];

if (!databaseUrl || !fileArg) {
  console.error("Usage: node scripts/supabase_import/apply_sql_file.cjs <database-url> <sql-file>");
  process.exit(1);
}

const file = path.resolve(fileArg);

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  try {
    const sql = fs.readFileSync(file, "utf8");
    console.log(`Running ${file}`);
    const result = await client.query(sql);
    if (Array.isArray(result)) {
      const last = result[result.length - 1];
      if (last?.rows?.length) console.table(last.rows);
    } else if (result.rows?.length) {
      console.table(result.rows);
    }
    console.log("Done.");
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
