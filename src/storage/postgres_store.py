"""PostgreSQL persistence for reconstructed SEC statement outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import Json, execute_values


@dataclass
class PostgresConfig:
    """Connection configuration for PostgreSQL."""

    dbname: str
    user: str
    host: str = "localhost"
    port: str = "5432"
    password: str | None = None


class PostgresStore:
    """Writes reconstructed tables and validation reports into PostgreSQL."""

    def __init__(self, config: Dict[str, str], schema: str = "public"):
        self.config = PostgresConfig(**config)
        self.schema = schema
        self.conn: PGConnection | None = None

    def __enter__(self) -> "PostgresStore":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        if self.conn is not None:
            return
        kwargs = {
            "dbname": self.config.dbname,
            "user": self.config.user,
            "host": self.config.host,
            "port": self.config.port,
        }
        if self.config.password:
            kwargs["password"] = self.config.password
        self.conn = psycopg2.connect(**kwargs)
        self.conn.autocommit = False

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _ensure_conn(self) -> PGConnection:
        if self.conn is None:
            self.connect()
        assert self.conn is not None
        return self.conn

    def ensure_schema(self) -> None:
        conn = self._ensure_conn()
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.statement_rows (
                    adsh TEXT NOT NULL,
                    stmt TEXT NOT NULL,
                    report INTEGER NOT NULL,
                    line INTEGER NOT NULL,
                    depth INTEGER,
                    rfile TEXT,
                    tag TEXT,
                    version TEXT,
                    label TEXT,
                    negating TEXT,
                    value DOUBLE PRECISION,
                    display_value DOUBLE PRECISION,
                    formatted_value TEXT,
                    uom TEXT,
                    ddate TEXT,
                    qtrs INTEGER,
                    segments TEXT,
                    coreg TEXT,
                    candidate_count INTEGER,
                    has_value BOOLEAN,
                    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (adsh, stmt, report, line)
                );
                """
            )
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.validation_reports (
                    adsh TEXT PRIMARY KEY,
                    summary_status TEXT,
                    summary_rows_total INTEGER,
                    summary_rows_with_values INTEGER,
                    summary_coverage_ratio DOUBLE PRECISION,
                    report_json JSONB NOT NULL,
                    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()

    def write_statement_tables(self, adsh: str, tables: Dict[str, pd.DataFrame]) -> int:
        """Upsert reconstructed statement rows and return row count written."""
        conn = self._ensure_conn()
        self.ensure_schema()

        all_rows = []
        for stmt, table in tables.items():
            if table.empty:
                continue
            for _, row in table.iterrows():
                all_rows.append(
                    (
                        adsh,
                        stmt,
                        self._to_int(row.get("report")),
                        self._to_int(row.get("line")),
                        self._to_int(row.get("inpth")),
                        row.get("rfile"),
                        row.get("tag"),
                        row.get("version"),
                        row.get("label"),
                        row.get("negating"),
                        self._to_float(row.get("value")),
                        self._to_float(row.get("display_value")),
                        row.get("formatted_value"),
                        row.get("uom"),
                        self._to_str(row.get("ddate")),
                        self._to_int(row.get("qtrs")),
                        self._to_str(row.get("segments")),
                        self._to_str(row.get("coreg")),
                        self._to_int(row.get("candidate_count")),
                        self._to_bool(row.get("has_value")),
                    )
                )

        if not all_rows:
            return 0

        insert_sql = f"""
            INSERT INTO {self.schema}.statement_rows (
                adsh, stmt, report, line, depth, rfile, tag, version, label, negating,
                value, display_value, formatted_value, uom, ddate, qtrs, segments, coreg,
                candidate_count, has_value
            ) VALUES %s
            ON CONFLICT (adsh, stmt, report, line) DO UPDATE SET
                depth = EXCLUDED.depth,
                rfile = EXCLUDED.rfile,
                tag = EXCLUDED.tag,
                version = EXCLUDED.version,
                label = EXCLUDED.label,
                negating = EXCLUDED.negating,
                value = EXCLUDED.value,
                display_value = EXCLUDED.display_value,
                formatted_value = EXCLUDED.formatted_value,
                uom = EXCLUDED.uom,
                ddate = EXCLUDED.ddate,
                qtrs = EXCLUDED.qtrs,
                segments = EXCLUDED.segments,
                coreg = EXCLUDED.coreg,
                candidate_count = EXCLUDED.candidate_count,
                has_value = EXCLUDED.has_value,
                updated_at = NOW();
        """

        with conn.cursor() as cur:
            execute_values(cur, insert_sql, all_rows, page_size=1000)
        conn.commit()
        return len(all_rows)

    def write_validation_report(self, adsh: str, report: Dict[str, object]) -> None:
        """Upsert one filing validation report as JSONB + summary fields."""
        conn = self._ensure_conn()
        self.ensure_schema()

        summary = report.get("summary", {})
        payload = (
            adsh,
            self._to_str(summary.get("status")),
            self._to_int(summary.get("rows_total")),
            self._to_int(summary.get("rows_with_values")),
            self._to_float(summary.get("overall_coverage_ratio")),
            Json(report),
        )

        sql = f"""
            INSERT INTO {self.schema}.validation_reports (
                adsh, summary_status, summary_rows_total, summary_rows_with_values,
                summary_coverage_ratio, report_json
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (adsh) DO UPDATE SET
                summary_status = EXCLUDED.summary_status,
                summary_rows_total = EXCLUDED.summary_rows_total,
                summary_rows_with_values = EXCLUDED.summary_rows_with_values,
                summary_coverage_ratio = EXCLUDED.summary_coverage_ratio,
                report_json = EXCLUDED.report_json,
                updated_at = NOW();
        """

        with conn.cursor() as cur:
            cur.execute(sql, payload)
        conn.commit()

    @staticmethod
    def _to_int(value):
        if value is None or pd.isna(value):
            return None
        return int(value)

    @staticmethod
    def _to_float(value):
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _to_str(value):
        if value is None or pd.isna(value):
            return None
        return str(value)

    @staticmethod
    def _to_bool(value):
        if value is None or pd.isna(value):
            return None
        return bool(value)
