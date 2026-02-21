"""Financial statement reconstruction logic."""

from typing import Dict, Optional, Tuple

import pandas as pd

from src.models import (
    BalanceSheet,
    CashFlowStatement,
    Company,
    FinancialStatement,
    IncomeStatement,
)
from src.parsers import NumericParser, PresentationParser, TagParser


class StatementReconstructor:
    """
    Reconstructs SEC statements from presentation rows and numeric facts.

    The table reconstruction APIs are the source of truth: rows come from
    pre.txt order/indentation and values are resolved from num.txt.
    """

    BALANCE_SHEET_CODES = ["BS", "BS-LND", "BS-ALT"]
    INCOME_STATEMENT_CODES = ["IS", "IS-COND"]
    CASH_FLOW_CODES = ["CF", "CF-INDIRECT", "CF-DIRECT"]
    CORE_STATEMENT_CODES = ["BS", "IS", "CF", "EQ", "CI"]

    def __init__(
        self,
        numeric_parser: NumericParser,
        presentation_parser: PresentationParser,
        tag_parser: TagParser,
    ):
        self.numeric_parser = numeric_parser
        self.presentation_parser = presentation_parser
        self.tag_parser = tag_parser

    @staticmethod
    def _parse_ddate(ddate: object) -> Optional[pd.Timestamp]:
        if pd.isna(ddate):
            return None
        parsed = pd.to_datetime(str(ddate), format="%Y%m%d", errors="coerce")
        return None if pd.isna(parsed) else parsed

    @staticmethod
    def _derive_period_start(period_end: pd.Timestamp, quarter_count: Optional[int]) -> pd.Timestamp:
        if not quarter_count or quarter_count <= 0:
            return period_end
        return period_end - pd.DateOffset(months=quarter_count * 3) + pd.Timedelta(days=1)

    @staticmethod
    def _primary_context_rows(df: pd.DataFrame) -> pd.DataFrame:
        """
        Prefer consolidated (no coreg/segments) rows for mapping.
        Fallback to all rows if no consolidated rows exist.
        """
        if df.empty:
            return df
        no_coreg = df["coreg"].isna() | (df["coreg"] == "")
        no_segments = df["segments"].isna() | (df["segments"] == "")
        primary = df[no_coreg & no_segments]
        return primary if not primary.empty else df

    def _select_latest_period_facts(
        self, adsh: str
    ) -> Tuple[pd.DataFrame, Optional[pd.Timestamp], Optional[int]]:
        facts = self.numeric_parser.get_facts_by_adsh(adsh)
        if facts.empty:
            return facts, None, None

        facts = self._primary_context_rows(facts.copy())
        duration_facts = facts[facts["qtrs"].notna() & (facts["qtrs"] > 0)].copy()
        if duration_facts.empty:
            return duration_facts, None, None

        duration_facts["ddate_ts"] = pd.to_datetime(
            duration_facts["ddate"], format="%Y%m%d", errors="coerce"
        )
        duration_facts = duration_facts[duration_facts["ddate_ts"].notna()]
        if duration_facts.empty:
            return duration_facts, None, None

        latest_end = duration_facts["ddate_ts"].max()
        latest_facts = duration_facts[duration_facts["ddate_ts"] == latest_end].copy()
        if latest_facts.empty:
            return latest_facts, latest_end, None

        qtrs = latest_facts["qtrs"].mode(dropna=True)
        quarter_count = int(qtrs.iloc[0]) if not qtrs.empty else None
        if quarter_count is not None:
            latest_facts = latest_facts[latest_facts["qtrs"] == quarter_count].copy()

        return latest_facts, latest_end, quarter_count

    def _derive_period_label(self, adsh: str, fallback_filing_date: str) -> str:
        _, latest_end, quarter_count = self._select_latest_period_facts(adsh)
        if latest_end is None:
            fallback = pd.Timestamp(fallback_filing_date)
            return f"FY-{fallback.year}"

        year = latest_end.year
        if quarter_count == 4:
            return f"FY-{year}"
        if quarter_count in {1, 2, 3}:
            return f"Q{quarter_count}-{year}"
        if quarter_count:
            return f"P{quarter_count}-{year}"
        return f"FY-{year}"

    def _resolve_statement_context(
        self, adsh: str, stmt_code: str, statement_tags: pd.Series
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Infer a single (ddate, qtrs) context for a statement table.
        """
        all_facts = self.numeric_parser.get_facts_by_adsh(adsh)
        if all_facts.empty:
            return None, None

        def filter_candidates(source: pd.DataFrame) -> pd.DataFrame:
            candidates = source[source["tag"].isin(statement_tags)]
            if candidates.empty:
                return candidates
            if stmt_code in self.BALANCE_SHEET_CODES:
                return candidates[candidates["qtrs"] == 0]
            return candidates[candidates["qtrs"].notna() & (candidates["qtrs"] > 0)]

        facts = filter_candidates(self._primary_context_rows(all_facts.copy()))
        if facts.empty:
            facts = filter_candidates(all_facts.copy())

        if facts.empty:
            return None, None

        facts["ddate_ts"] = pd.to_datetime(facts["ddate"], format="%Y%m%d", errors="coerce")
        facts = facts[facts["ddate_ts"].notna()]
        if facts.empty:
            return None, None

        target_date = facts["ddate_ts"].max()
        same_date = facts[facts["ddate_ts"] == target_date]
        qtrs_mode = same_date["qtrs"].mode(dropna=True)
        target_qtrs = int(qtrs_mode.iloc[0]) if not qtrs_mode.empty else None

        return target_date.strftime("%Y%m%d"), target_qtrs

    @staticmethod
    def _apply_sign_rules(stmt_code: str, tag: str, value: float, negating: str) -> float:
        """Apply statement-aware sign handling; avoid blind inversions."""
        signed = -value if str(negating) == "1" else value
        tag_lower = tag.lower()

        if stmt_code == "CF":
            if any(x in tag_lower for x in ["payment", "repurchase", "repay", "purchase"]):
                signed = -abs(signed)
            elif any(x in tag_lower for x in ["proceeds", "issuance", "borrowings", "borrow"]):
                signed = abs(signed)

        if stmt_code == "EQ":
            if any(x in tag_lower for x in ["dividend", "repurchase", "purchases", "payment"]):
                signed = -abs(signed)

        return signed

    @staticmethod
    def _format_display_value(display_value: Optional[float]) -> Optional[str]:
        """Format numeric values with financial-style parentheses for negatives."""
        if display_value is None or pd.isna(display_value):
            return None

        rounded = round(float(display_value), 2)
        if float(rounded).is_integer():
            abs_text = f"{abs(int(rounded)):,}"
        else:
            abs_text = f"{abs(rounded):,.2f}"
        return f"({abs_text})" if rounded < 0 else abs_text

    def _reconstruct_ci_fallback(
        self, adsh: str, ddate: Optional[str] = None, qtrs: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Build CI table from num.txt when no standalone CI structure exists in pre.txt.
        """
        facts = self.numeric_parser.get_facts_by_adsh(adsh)
        if facts.empty:
            return pd.DataFrame()

        ci_mask = facts["tag"].str.contains("ComprehensiveIncome", na=False, case=False)
        facts = facts[ci_mask].copy()
        facts = facts[facts["qtrs"].notna() & (facts["qtrs"] > 0)]
        if facts.empty:
            return pd.DataFrame()

        if ddate is not None:
            facts = facts[facts["ddate"] == str(ddate)]
        if qtrs is not None:
            facts = facts[facts["qtrs"] == int(qtrs)]

        if facts.empty:
            return pd.DataFrame()

        if ddate is None or qtrs is None:
            facts["ddate_ts"] = pd.to_datetime(facts["ddate"], format="%Y%m%d", errors="coerce")
            facts = facts[facts["ddate_ts"].notna()]
            if facts.empty:
                return pd.DataFrame()
            latest = facts["ddate_ts"].max()
            facts = facts[facts["ddate_ts"] == latest]
            if qtrs is None:
                qtrs_mode = facts["qtrs"].mode(dropna=True)
                if not qtrs_mode.empty:
                    facts = facts[facts["qtrs"] == int(qtrs_mode.iloc[0])]

        rows = []
        for i, (tag, group) in enumerate(facts.groupby("tag"), start=1):
            chosen = self._choose_preferred_fact(group)
            if chosen is None:
                continue

            raw_value = None if pd.isna(chosen["value"]) else float(chosen["value"])
            display_value = (
                self._apply_sign_rules("CI", str(tag), raw_value, "0")
                if raw_value is not None
                else None
            )
            label = self.tag_parser.get_tag_label(str(tag)) if self.tag_parser else str(tag)

            rows.append(
                {
                    "adsh": adsh,
                    "stmt": "CI",
                    "report": 0,
                    "line": i,
                    "inpth": 0,
                    "rfile": "D",
                    "tag": str(tag),
                    "version": chosen.get("version"),
                    "label": label or str(tag),
                    "negating": "0",
                    "value": raw_value,
                    "display_value": display_value,
                    "formatted_value": self._format_display_value(display_value),
                    "uom": chosen.get("uom"),
                    "ddate": chosen.get("ddate"),
                    "qtrs": None if pd.isna(chosen.get("qtrs")) else int(chosen.get("qtrs")),
                    "segments": chosen.get("segments"),
                    "coreg": chosen.get("coreg"),
                    "has_value": raw_value is not None,
                }
            )

        return pd.DataFrame(rows).sort_values(["line"]).reset_index(drop=True)

    @staticmethod
    def _choose_preferred_fact(matches: pd.DataFrame) -> Optional[pd.Series]:
        if matches.empty:
            return None

        scored = matches.copy()
        scored["coreg_rank"] = (~(scored["coreg"].isna() | (scored["coreg"] == ""))).astype(int)
        scored["segments_rank"] = (~(scored["segments"].isna() | (scored["segments"] == ""))).astype(
            int
        )
        scored["abs_value"] = scored["value"].abs().fillna(0)
        scored = scored.sort_values(
            ["coreg_rank", "segments_rank", "abs_value"], ascending=[True, True, False]
        )
        return scored.iloc[0]

    def reconstruct_statement_table(
        self,
        adsh: str,
        stmt_code: str,
        ddate: Optional[str] = None,
        qtrs: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Reconstruct one statement as a row-accurate table from pre.txt + num.txt.
        """
        structure = self.presentation_parser.get_statement_structure(adsh, stmt_code)
        if structure.empty:
            if stmt_code == "CI":
                return self._reconstruct_ci_fallback(adsh, ddate=ddate, qtrs=qtrs)
            return pd.DataFrame()

        structure = structure.sort_values(["report", "line"]).reset_index(drop=True)
        tag_set = structure["tag"].dropna().astype(str)

        target_ddate, target_qtrs = ddate, qtrs
        if target_ddate is None or target_qtrs is None:
            inferred_ddate, inferred_qtrs = self._resolve_statement_context(adsh, stmt_code, tag_set)
            if target_ddate is None:
                target_ddate = inferred_ddate
            if target_qtrs is None:
                target_qtrs = inferred_qtrs

        facts = self.numeric_parser.get_facts_by_adsh(adsh)
        facts = facts[facts["tag"].isin(tag_set)]
        if target_ddate is not None:
            facts = facts[facts["ddate"] == str(target_ddate)]
        if target_qtrs is not None:
            facts = facts[facts["qtrs"] == int(target_qtrs)]

        rows = []
        for _, srow in structure.iterrows():
            tag = srow["tag"]
            version = srow["version"]
            matches = facts[facts["tag"] == tag]
            if pd.notna(version):
                matches = matches[matches["version"] == version]
            chosen = self._choose_preferred_fact(matches)

            value = None
            display_value = None
            uom = None
            resolved_ddate = target_ddate
            resolved_qtrs = target_qtrs
            segments = None
            coreg = None

            if chosen is not None:
                value = None if pd.isna(chosen["value"]) else float(chosen["value"])
                if value is not None:
                    display_value = self._apply_sign_rules(
                        stmt_code, str(tag), value, str(srow.get("negating", "0"))
                    )
                uom = chosen["uom"]
                resolved_ddate = chosen["ddate"]
                resolved_qtrs = (
                    None if pd.isna(chosen["qtrs"]) else int(chosen["qtrs"])
                )
                segments = chosen["segments"]
                coreg = chosen["coreg"]

            rows.append(
                {
                    "adsh": adsh,
                    "stmt": stmt_code,
                    "report": srow["report"],
                    "line": srow["line"],
                    "inpth": srow["inpth"],
                    "rfile": srow["rfile"],
                    "tag": tag,
                    "version": version,
                    "label": srow["plabel"] if pd.notna(srow["plabel"]) else tag,
                    "negating": srow["negating"],
                    "value": value,
                    "display_value": display_value,
                    "formatted_value": self._format_display_value(display_value),
                    "uom": uom,
                    "ddate": resolved_ddate,
                    "qtrs": resolved_qtrs,
                    "segments": segments,
                    "coreg": coreg,
                    "has_value": value is not None,
                }
            )

        return pd.DataFrame(rows)

    def get_statement_coverage(self, adsh: str, stmt_code: str) -> Dict[str, object]:
        """Return lightweight validation/coverage metrics for one statement."""
        table = self.reconstruct_statement_table(adsh, stmt_code)
        if table.empty:
            return {
                "stmt": stmt_code,
                "rows_total": 0,
                "rows_with_values": 0,
                "rows_missing_values": 0,
                "coverage_ratio": 0.0,
                "missing_tags": [],
            }

        missing = table[~table["has_value"]]
        rows_total = int(len(table))
        rows_with_values = int(table["has_value"].sum())
        coverage_ratio = (rows_with_values / rows_total) if rows_total else 0.0
        return {
            "stmt": stmt_code,
            "rows_total": rows_total,
            "rows_with_values": rows_with_values,
            "rows_missing_values": int(len(missing)),
            "coverage_ratio": coverage_ratio,
            "missing_tags": missing["tag"].tolist(),
        }

    def reconstruct_filing_tables(
        self, adsh: str, statement_codes: Optional[list[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        codes = statement_codes or self.CORE_STATEMENT_CODES
        output: Dict[str, pd.DataFrame] = {}
        for code in codes:
            output[code] = self.reconstruct_statement_table(adsh, code)
        return output

    def reconstruct_balance_sheet(
        self,
        adsh: str,
        company: Company,
        as_of_date: Optional[str] = None,
    ) -> Optional[BalanceSheet]:
        bs_table = self.reconstruct_statement_table(adsh, "BS")
        if bs_table.empty:
            return None

        bs_values = bs_table[bs_table["has_value"]].copy()
        derived_as_of = pd.Timestamp.now().date()
        if as_of_date:
            derived_as_of = pd.Timestamp(as_of_date).date()
        else:
            max_ddate = bs_values["ddate"].dropna().max() if not bs_values.empty else None
            parsed_ddate = self._parse_ddate(max_ddate)
            if parsed_ddate is not None:
                derived_as_of = parsed_ddate.date()

        balance_sheet = BalanceSheet(
            company=company,
            as_of_date=derived_as_of,
            assets={},
            liabilities={},
            equity={},
        )

        for _, row in bs_values.iterrows():
            tag = str(row["tag"])
            label = str(row["label"])
            value = float(row["display_value"])

            if "asset" in tag.lower():
                balance_sheet.assets[label] = value
            elif any(x in tag.lower() for x in ["liab", "payable"]):
                balance_sheet.liabilities[label] = value
            elif any(x in tag.lower() for x in ["equity", "stockholders", "common"]):
                balance_sheet.equity[label] = value

        return balance_sheet

    def reconstruct_income_statement(
        self,
        adsh: str,
        company: Company,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> Optional[IncomeStatement]:
        is_table = self.reconstruct_statement_table(adsh, "IS")
        if is_table.empty:
            return None

        values = is_table[is_table["has_value"]].copy()
        max_ddate = values["ddate"].dropna().max() if not values.empty else None
        parsed_end = self._parse_ddate(max_ddate) or pd.Timestamp.now()
        quarter_count = int(values["qtrs"].dropna().mode().iloc[0]) if not values.empty else 1
        parsed_start = self._derive_period_start(parsed_end, quarter_count)

        income_statement = IncomeStatement(
            company=company,
            period_start=pd.Timestamp(period_start).date() if period_start else parsed_start.date(),
            period_end=pd.Timestamp(period_end).date() if period_end else parsed_end.date(),
            revenues={},
            expenses={},
            income={},
        )

        for _, row in values.iterrows():
            tag = str(row["tag"])
            label = str(row["label"])
            value = float(row["display_value"])

            if any(x in tag.lower() for x in ["revenue", "sales"]):
                income_statement.revenues[label] = value
            elif any(x in tag.lower() for x in ["expense", "cost", "depreciation"]):
                income_statement.expenses[label] = value
            elif any(x in tag.lower() for x in ["earnings", "profit", "loss", "income"]):
                income_statement.income[label] = value

        return income_statement

    def reconstruct_cash_flow_statement(
        self,
        adsh: str,
        company: Company,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> Optional[CashFlowStatement]:
        cf_table = self.reconstruct_statement_table(adsh, "CF")
        if cf_table.empty:
            return None

        values = cf_table[cf_table["has_value"]].copy()
        max_ddate = values["ddate"].dropna().max() if not values.empty else None
        parsed_end = self._parse_ddate(max_ddate) or pd.Timestamp.now()
        quarter_count = int(values["qtrs"].dropna().mode().iloc[0]) if not values.empty else 1
        parsed_start = self._derive_period_start(parsed_end, quarter_count)

        cash_flow = CashFlowStatement(
            company=company,
            period_start=pd.Timestamp(period_start).date() if period_start else parsed_start.date(),
            period_end=pd.Timestamp(period_end).date() if period_end else parsed_end.date(),
            operating_activities={},
            investing_activities={},
            financing_activities={},
        )

        for _, row in values.iterrows():
            tag = str(row["tag"])
            label = str(row["label"])
            value = float(row["display_value"])

            if any(x in tag.lower() for x in ["operating", "depreciation", "amortization"]):
                cash_flow.operating_activities[label] = value
            elif any(x in tag.lower() for x in ["invest", "capital", "property"]):
                cash_flow.investing_activities[label] = value
            elif any(x in tag.lower() for x in ["financ", "debt", "equity", "dividend"]):
                cash_flow.financing_activities[label] = value

        return cash_flow

    def reconstruct_full_statement(
        self,
        adsh: str,
        company: Company,
        filing_date: str,
    ) -> Optional[FinancialStatement]:
        balance_sheet = self.reconstruct_balance_sheet(adsh, company)
        income_statement = self.reconstruct_income_statement(adsh, company)
        cash_flow = self.reconstruct_cash_flow_statement(adsh, company)

        if not any([balance_sheet, income_statement, cash_flow]):
            return None

        return FinancialStatement(
            company=company,
            period=self._derive_period_label(adsh, filing_date),
            filing_date=pd.Timestamp(filing_date).date(),
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            cash_flow_statement=cash_flow,
            metadata={"adsh": adsh},
        )
