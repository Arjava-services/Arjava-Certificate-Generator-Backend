from typing import List, Dict, Any, Set
from app.schemas.sheets import SheetValidationResult, ValidationErrorItem
from app.models.entities import ProjectFieldMapping

class ValidationService:
    def validate_spreadsheet_data(
        self,
        rows: List[Dict[str, Any]],
        mappings: List[ProjectFieldMapping]
    ) -> SheetValidationResult:
        """
        Validates participant rows against required fields and project mappings.
        Detects:
        - Missing name
        - Missing required fields
        - Empty rows
        - Duplicate participants
        - Invalid data
        """
        issues: List[ValidationErrorItem] = []
        seen_entries: Dict[tuple, int] = {}
        valid_count = 0

        # Find which column maps to name
        name_column = None
        required_columns = []
        for m in mappings:
            col = m.sheet_column
            if not col:
                continue
            if "{{name}}" in m.placeholder.lower() or "name" in m.placeholder.lower():
                name_column = col
            if m.is_required:
                required_columns.append((m.placeholder, col))

        # If name placeholder wasn't found specifically, check for common header 'Name'
        if not name_column and rows:
            for c in rows[0].keys():
                if c.lower() in ("name", "participant name", "full name", "student name"):
                    name_column = c
                    break

        for idx, row in enumerate(rows):
            row_num = row.get("_row_number", idx + 2)
            
            # Check if row is completely empty
            row_values = [str(v).strip() for k, v in row.items() if not k.startswith("_")]
            if not any(row_values):
                issues.append(ValidationErrorItem(
                    row_number=row_num,
                    issue_type="empty_row",
                    message=f"Row {row_num}: Entire row is empty.",
                    severity="error",
                    row_data=row
                ))
                continue

            has_error = False

            # Check Name column
            if name_column:
                name_val = str(row.get(name_column, "")).strip()
                if not name_val:
                    issues.append(ValidationErrorItem(
                        row_number=row_num,
                        column_name=name_column,
                        issue_type="missing_value",
                        message=f"Row {row_num}: Participant Name is missing.",
                        severity="error",
                        row_data=row
                    ))
                    has_error = True

            # Check for duplicate entry (identical data across all sheet columns e.g. name, class, college)
            # A row is ONLY considered a duplicate entry if all data values match an earlier row identically.
            # Duplicate data is never stopped - it remains valid for generation.
            clean_entry = tuple(
                (k.strip().lower(), str(v).strip().lower())
                for k, v in sorted(row.items())
                if not k.startswith("_") and str(v).strip()
            )
            if clean_entry:
                if clean_entry in seen_entries:
                    prev_row = seen_entries[clean_entry]
                    issues.append(ValidationErrorItem(
                        row_number=row_num,
                        column_name=name_column or "Row",
                        issue_type="duplicate_entry",
                        message=f"Row {row_num}: Duplicate entry (identical to row {prev_row}).",
                        severity="warning",
                        row_data=row
                    ))
                else:
                    seen_entries[clean_entry] = row_num

            # Check other mapped required fields
            for placeholder, col in required_columns:
                if col == name_column:
                    continue
                val = str(row.get(col, "")).strip()
                if not val:
                    issues.append(ValidationErrorItem(
                        row_number=row_num,
                        column_name=col,
                        issue_type="missing_value",
                        message=f"Row {row_num}: Missing required field '{col}' for placeholder {placeholder}.",
                        severity="warning",
                        row_data=row
                    ))

            if not has_error:
                valid_count += 1

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        return SheetValidationResult(
            is_valid=(error_count == 0 and valid_count > 0),
            total_rows=len(rows),
            valid_rows_count=valid_count,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues
        )

validation_service = ValidationService()
