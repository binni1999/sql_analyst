
export function formatValue(value) {
    if (value === null || value === undefined) {
        return "";
    }

    if (typeof value === "number" && Number.isFinite(value)) {
        return Number.isInteger(value)
            ? String(value)
            : value.toFixed(2);
    }

    if (typeof value === "string") {
        const trimmed = value.trim();

        // Only format strings that look explicitly decimal.
        // This avoids changing integer IDs such as "15".
        if (
            trimmed !== "" &&
            /^[-+]?\d+\.\d+$/.test(trimmed) &&
            Number.isFinite(Number(trimmed))
        ) {
            return Number(trimmed).toFixed(2);
        }
    }

    return value;
}
