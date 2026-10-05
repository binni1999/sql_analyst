function ResultTable({ result }) {
    if (!result) {
        return null;
    }

    return (
        <section className="result-section">
            <h2>Query Result</h2>

            <p>
                Rows returned:{" "}
                <strong>{result.row_count}</strong>
            </p>

            {result.data?.length > 0 && (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                {result.columns.map((column) => (
                                    <th key={column}>{column}</th>
                                ))}
                            </tr>
                        </thead>

                        <tbody>
                            {result.data.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {result.columns.map((column) => (
                                        <td key={column}>
                                            {row[column]}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}

export default ResultTable;