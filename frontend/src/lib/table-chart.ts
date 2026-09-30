/** Minimal markdown-table reader used as a chart fallback.
 *
 * The configured default model, llama3.1 (1.2B), ignores the chart instruction
 * and answers numeric questions with a GitHub-flavoured markdown table instead.
 * Parsing that table is what makes charts appear without switching models.
 */

export type TableChartKind = "bar" | "line" | "pie";

export type TableChart = {
  kind: TableChartKind;
  title: string;
  data: { label: string; value: number }[];
};

const MAX_ROWS = 60;
const DELIMITER = /^\s*\|?[\s:|-]+\|[\s:|-]*$/;

/** Parse the first number in a cell, tolerating units, currency, and separators. */
function toNumber(cell: string): number | null {
  const cleaned = cell.replace(/[,\s]/g, "").replace(/[^0-9.eE+-]/g, "");
  if (!cleaned || !/\d/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

/**
 * Find a two-column markdown table (label + a single numeric column) and turn it
 * into a chart. Anything more elaborate is left alone, because guessing the
 * intended series out of a wide table produces a misleading picture.
 */
export function tableToChart(text: string): TableChart | null {
  if (!text || !text.includes("|")) return null;

  const lines = text.split("\n");
  for (let index = 0; index < lines.length - 1; index += 1) {
    const header = splitRow(lines[index]);
    const separator = lines[index + 1]?.trim() ?? "";

    if (header.length < 2 || header.length > 2) continue;
    if (!DELIMITER.test(separator)) continue;
    if (separator.split("|").length < 2) continue;

    const rows: { label: string; value: number }[] = [];
    for (let row = index + 2; row < lines.length; row += 1) {
      const line = lines[row].trim();
      if (!line || !line.includes("|")) break;

      const cells = splitRow(line);
      if (cells.length < 2) break;

      const label = cells[0].replace(/\*\*|__/g, "").trim();
      const value = toNumber(cells[1]);
      if (!label || value === null) break;

      rows.push({ label: label.slice(0, 40), value });
      if (rows.length >= MAX_ROWS) break;
    }

    if (rows.length < 2) continue;

    return {
      kind: "bar",
      title: header[0] ? `${header[0]} by ${header[1]}` : "",
      data: rows,
    };
  }

  return null;
}
