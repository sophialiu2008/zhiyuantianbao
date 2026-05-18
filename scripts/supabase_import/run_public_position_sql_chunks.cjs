const fs = require("fs");
const path = require("path");
const { Client } = require("../../tools/pg-client/node_modules/pg");

const databaseUrl = process.argv[2] || process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("Missing database URL.");
  process.exit(1);
}

const root = path.resolve(__dirname, "..", "..");
const schemaFile = path.join(root, "supabase", "migrations", "023_public_position_schema.sql");
const chunkDir = path.join(root, "data", "enriched", "public_positions", "import_chunks");

const files = [
  schemaFile,
  ...fs.readdirSync(chunkDir)
    .filter((name) => name.endsWith(".sql"))
    .sort((a, b) => a.localeCompare(b))
    .map((name) => path.join(chunkDir, name)),
];

async function main() {
  const client = new Client({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();
  console.log(`Connected. Running ${files.length} SQL files.`);
  try {
    for (const file of files) {
      const sql = fs.readFileSync(file, "utf8");
      const name = path.relative(root, file);
      const startedAt = Date.now();
      console.log(`\n>>> ${name}`);
      const result = await client.query(sql);
      const elapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
      if (Array.isArray(result)) {
        const last = result[result.length - 1];
        if (last?.rows?.length) console.table(last.rows);
      } else if (result.rows?.length) {
        console.table(result.rows);
      }
      console.log(`Done in ${elapsed}s`);
    }
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error("\nSQL batch failed.");
  console.error(error.message);
  process.exit(1);
});
