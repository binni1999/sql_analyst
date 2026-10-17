import { useMemo, useState } from "react";
import { formatValue } from "../utils/formatValue";

const PAGE_SIZE = 10;
const EMPTY_ROWS = [];

function ResultTable({ result }) {
    const [currentPage, setCurrentPage] = useState(1);
    const [sort, setSort] = useState({ column: null, direction: "asc" });

    const columns = result?.columns ?? [];
    const rows = result?.data ?? EMPTY_ROWS;
    const totalRows = Number.isFinite(Number(result?.row_count)) ? Number(result.row_count) : rows.length;
    const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    const safePage = Math.min(currentPage, totalPages);

    const sortedRows = useMemo(() => {
        if (!sort.column) return rows;
        return [...rows].sort((a, b) => {
            const left = a?.[sort.column];
            const right = b?.[sort.column];
            if (left == null && right == null) return 0;
            if (left == null) return 1;
            if (right == null) return -1;
            const leftNumber = Number(left);
            const rightNumber = Number(right);
            const comparison = left !== "" && right !== "" && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)
                ? leftNumber - rightNumber
                : String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
            return sort.direction === "asc" ? comparison : -comparison;
        });
    }, [rows, sort]);

    if (!result) return null;

    const startIndex = (safePage - 1) * PAGE_SIZE;
    const visibleRows = sortedRows.slice(startIndex, startIndex + PAGE_SIZE);
    const endIndex = Math.min(startIndex + visibleRows.length, rows.length);

    const toggleSort = (column) => {
        setSort((previous) => ({
            column,
            direction: previous.column === column && previous.direction === "asc" ? "desc" : "asc",
        }));
        setCurrentPage(1);
    };

    return (
        <section className="result-section">
            <div className="section-heading-row">
                <h2>Query Result</h2>
                <span className="result-count-pill">{totalRows.toLocaleString()} rows</span>
            </div>
            <p className="result-subtitle">{rows.length ? `Showing ${startIndex + 1}–${endIndex} of ${rows.length} returned rows` : `Rows returned: ${totalRows}`}</p>
            {rows.length > 0 && columns.length > 0 && (
                <>
                    <div className="table-container">
                        <table>
                            <thead><tr>{columns.map((column) => (
                                <th key={column} scope="col">
                                    <button type="button" className="table-sort-button" onClick={() => toggleSort(column)} aria-label={`Sort by ${column}`}>
                                        {column}<span aria-hidden="true">{sort.column === column ? (sort.direction === "asc" ? " ↑" : " ↓") : " ↕"}</span>
                                    </button>
                                </th>
                            ))}</tr></thead>
                            <tbody>{visibleRows.map((row, rowIndex) => (
                                <tr key={startIndex + rowIndex}>{columns.map((column) => (
                                    <td key={column}>{formatValue(row?.[column])}</td>
                                ))}</tr>
                            ))}</tbody>
                        </table>
                    </div>
                    {totalPages > 1 && (
                        <div className="pagination">
                            <span className="pagination-info">Showing {startIndex + 1}–{endIndex} of {rows.length}</span>
                            <div className="pagination-controls">
                                <button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={currentPage === 1}>Previous</button>
                                <span className="pagination-page">Page {safePage} of {totalPages}</span>
                                <button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))} disabled={safePage === totalPages}>Next</button>
                            </div>
                        </div>
                    )}
                </>
            )}
            {rows.length === 0 && <div className="empty-result-state">The query completed without returning any rows.</div>}
        </section>
    );
}

export default ResultTable;
