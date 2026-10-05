class ResultAnalyzer:

    def analyze(self, result: dict):

        columns = result["columns"]
        rows = result["rows"]

        # -----------------------------------------
        # Convert rows into dictionaries
        # -----------------------------------------

        data = []

        for row in rows:

            record = dict(
                zip(columns, row)
            )

            data.append(record)

        # -----------------------------------------
        # Analyze result
        # -----------------------------------------

        return {
            "row_count": len(rows),
            "columns": columns,
            "data": data,
            "is_empty": len(rows) == 0
        }