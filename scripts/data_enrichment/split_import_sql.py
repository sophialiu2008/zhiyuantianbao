#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split generated SQL import into small files for Supabase SQL Editor."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/enriched/school_profiles/import_school_profiles_enriched.sql")
    parser.add_argument("--output-dir", default="data/enriched/school_profiles/import_chunks")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8").strip()
    text = re.sub(r"^--.*?\nbegin;\s*", "", text, flags=re.S)
    text = re.sub(r"\s*commit;\s*$", "", text, flags=re.S)
    statements = [part.strip() + ";" for part in re.split(r";\s*\n\s*(?=insert into public\.)", text) if part.strip()]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.sql"):
      old.unlink()

    for index, statement in enumerate(statements, start=1):
        target = output_dir / f"{index:02d}_import.sql"
        target.write_text("begin;\n\n" + statement + "\n\ncommit;\n", encoding="utf-8")

    runner = output_dir / "README.md"
    runner.write_text(
        "# SQL 导入分片\n\n"
        "请在 Supabase SQL Editor 中按文件名顺序逐个执行这些 `.sql` 文件。\n\n"
        + "\n".join(f"- `{path.name}`" for path in sorted(output_dir.glob("*.sql")))
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(statements)} SQL chunks -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
