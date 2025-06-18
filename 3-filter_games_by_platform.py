import os
import sqlite3
from typing import List, Tuple, Any

SOURCE_DB = "game_data_live.db"
DEST_DB = "game_data_filtered.db"
TABLE_NAME = "games"

PLATFORM_KEYWORDS = ["PlayStation"]
MAX_DESCRIPTION_BYTES = 7900


def copy_schema(src_cur: sqlite3.Cursor, dst_cur: sqlite3.Cursor, table: str) -> None:
    """
    Replicates the CREATE TABLE statement of `table` from src to dst.
    """
    schema_row = src_cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if schema_row is None:
        raise RuntimeError(f"Table '{table}' not found in source DB")
    dst_cur.execute(schema_row[0])


def build_platform_filter_clause(keywords: List[str]) -> str:
    """
    Builds a SQL WHERE clause that checks if the `platforms` column contains
    at least one of the supplied keywords.
    """
    return " OR ".join(f"platforms LIKE '%' || ? || '%'" for _ in keywords)


def normalize_description(text: str | None) -> str | None:
    """Ensure UTF-8 compatibility and truncate to MAX_DESCRIPTION_BYTES."""
    if text is None:
        return None

    # Encode with replacement for any invalid sequences.
    encoded: bytes = str(text).encode("utf-8", errors="replace")

    # Trim to byte limit while preserving UTF-8 validity.
    if len(encoded) > MAX_DESCRIPTION_BYTES:
        encoded = encoded[:MAX_DESCRIPTION_BYTES]
        # Remove any trailing partial multibyte sequence.
        encoded = encoded.decode("utf-8", errors="ignore").encode("utf-8")
    return encoded.decode("utf-8", errors="ignore")


def transform_row(
    row_values: List[Any],
    col_idx: dict[str, int],
) -> Tuple[Any, ...]:
    """
    Apply all requested transformations to a row and return the new tuple.
    """
    # rating: 0  -> NULL
    rating_val = row_values[col_idx["rating"]]
    if rating_val == 0:
        row_values[col_idx["rating"]] = None

    # playtime: 0 -> NULL
    if "playtime" in col_idx:
        playtime_val = row_values[col_idx["playtime"]]
        if playtime_val == 0:
            row_values[col_idx["playtime"]] = None

    # background_image: '' -> NULL
    if "background_image" in col_idx:
        bg_val = row_values[col_idx["background_image"]]
        if bg_val is not None and str(bg_val).strip() == "":
            row_values[col_idx["background_image"]] = None

    # description: UTF-8 safe & ≤ MAX_DESCRIPTION_BYTES
    if "description" in col_idx:
        desc_val = row_values[col_idx["description"]]
        row_values[col_idx["description"]] = normalize_description(desc_val)

    return tuple(row_values)


def main() -> None:
    # Start fresh each run.
    if os.path.exists(DEST_DB):
        os.remove(DEST_DB)

    src_conn = sqlite3.connect(SOURCE_DB)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    dst_conn = sqlite3.connect(DEST_DB)
    dst_cur = dst_conn.cursor()

    # 1. Copy exact schema.
    copy_schema(src_cur, dst_cur, TABLE_NAME)
    dst_conn.commit()

    # 2. Column metadata and helpers.
    columns = [row["name"] for row in src_cur.execute(f"PRAGMA table_info({TABLE_NAME})")]
    column_list_sql = ", ".join(columns)
    placeholders_sql = ", ".join("?" * len(columns))
    col_idx = {name: idx for idx, name in enumerate(columns)}

    # 3. Select rows that match platform keywords.
    where_clause = build_platform_filter_clause(PLATFORM_KEYWORDS)
    src_cur.execute(
        f"SELECT {column_list_sql} FROM {TABLE_NAME} WHERE {where_clause}",
        PLATFORM_KEYWORDS,
    )

    # 4. Transform rows and bulk insert.
    transformed_rows: list[Tuple[Any, ...]] = []
    for row in src_cur:
        row_values = list(row)
        transformed_rows.append(transform_row(row_values, col_idx))

    if transformed_rows:
        dst_cur.executemany(
            f"INSERT INTO {TABLE_NAME} ({column_list_sql}) VALUES ({placeholders_sql})",
            transformed_rows,
        )
        dst_conn.commit()

    # 5. Clean-up.
    src_conn.close()
    dst_conn.close()
    print(
        f"Filtered database created with {len(transformed_rows)} rows at '{DEST_DB}'."
    )


if __name__ == "__main__":
    main()
