import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("synthetic_data", "business_exports");
await fs.mkdir(outputDir, { recursive: true });

let state = 20260807;
const random = () => {
  state = (state * 1664525 + 1013904223) >>> 0;
  return state / 4294967296;
};
const pick = (values) => values[Math.floor(random() * values.length)];
const integer = (min, max) => Math.floor(random() * (max - min + 1)) + min;
const csvCell = (value) => {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const toCsv = (headers, rows) => [headers, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n") + "\r\n";

const regions = ["North", "South", "East", "West", "Central"];
const products = ["Sentinel Core", "Forecast Studio", "Risk Monitor", "Data Fabric", "Executive Copilot", "Support Intelligence"];
const customers = Array.from({ length: 120 }, (_, index) => `Customer ${String(index + 1).padStart(3, "0")} ${pick(["Industries", "Holdings", "Systems", "Group", "Solutions"])}`);
const salesHeaders = ["Date", "Revenue", "Orders", "Cancelled", "Region", "Product", "Customer"];
const salesRows = [];
const start = new Date("2025-08-08T00:00:00Z");
for (let day = 0; day < 365; day += 1) {
  const date = new Date(start);
  date.setUTCDate(start.getUTCDate() + day);
  const isoDate = date.toISOString().slice(0, 10);
  for (let segment = 0; segment < 4; segment += 1) {
    const orders = integer(14, 85);
    const cancelled = Math.min(orders, Math.round(orders * (0.01 + random() * 0.08)));
    const averageOrderValue = integer(850, 6200);
    const seasonality = 1 + 0.14 * Math.sin((day / 365) * Math.PI * 2) + day / 365 * 0.12;
    const revenue = Math.round((orders - cancelled) * averageOrderValue * seasonality * 100) / 100;
    salesRows.push([isoDate, revenue, orders, cancelled, regions[(day + segment) % regions.length], pick(products), pick(customers)]);
  }
}

const issues = ["Delayed data refresh", "Dashboard access", "Incorrect revenue mapping", "Export failure", "Integration timeout", "Inventory mismatch", "Forecast variance", "User provisioning"];
const priorities = ["Low", "Medium", "Medium", "High", "Critical"];
const statuses = ["Open", "Pending", "Resolved", "Closed"];
const sentiments = ["Positive", "Neutral", "Negative"];
const supportHeaders = ["Ticket", "Issue", "Priority", "Status", "Sentiment"];
const supportRows = Array.from({ length: 600 }, (_, index) => {
  const priority = pick(priorities);
  const status = pick(statuses);
  const sentiment = status === "Resolved" || status === "Closed" ? pick(["Positive", "Positive", "Neutral"]) : priority === "Critical" ? "Negative" : pick(sentiments);
  return [`TKT-${String(index + 1).padStart(6, "0")}`, pick(issues), priority, status, sentiment];
});

const firstNames = ["Aarav", "Aditi", "Ananya", "Arjun", "Diya", "Ishaan", "Kavya", "Meera", "Neha", "Rohan", "Saanvi", "Vikram", "Zoya", "Rahul", "Priya"];
const lastNames = ["Sharma", "Verma", "Patel", "Singh", "Gupta", "Mehta", "Rao", "Kapoor", "Nair", "Joshi", "Malhotra", "Iyer"];
const departments = ["Engineering", "Sales", "Finance", "Customer Success", "Operations", "People & Culture", "Data Science", "Security"];
const performance = ["Needs Improvement", "Meets Expectations", "Exceeds Expectations", "Outstanding"];
const hrHeaders = ["Employee", "Department", "Leave", "Performance", "Joining"];
const hrRows = Array.from({ length: 200 }, (_, index) => {
  const joining = new Date("2018-01-01T00:00:00Z");
  joining.setUTCDate(joining.getUTCDate() + integer(0, 3000));
  return [`EMP-${String(index + 1).padStart(5, "0")} - ${pick(firstNames)} ${pick(lastNames)}`, pick(departments), integer(0, 24), pick(performance), joining.toISOString().slice(0, 10)];
});

const datasets = [
  { file: "Sales.csv", sheet: "Sales", headers: salesHeaders, rows: salesRows },
  { file: "Support.csv", sheet: "Support", headers: supportHeaders, rows: supportRows },
  { file: "HR.csv", sheet: "HR", headers: hrHeaders, rows: hrRows },
];

let workbook;
for (const [index, dataset] of datasets.entries()) {
  const csv = toCsv(dataset.headers, dataset.rows);
  await fs.writeFile(path.join(outputDir, dataset.file), csv, "utf8");
  if (index === 0) workbook = await Workbook.fromCSV(csv, { sheetName: dataset.sheet });
  else await workbook.fromCSV(csv, { sheetName: dataset.sheet });
}

for (const dataset of datasets) {
  const sheet = workbook.worksheets.getItem(dataset.sheet);
  const used = sheet.getUsedRange();
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  used.format.font = { name: "Aptos", size: 10, color: "#243044" };
  used.format.rowHeight = 20;
  const header = sheet.getRangeByIndexes(0, 0, 1, dataset.headers.length);
  header.format = { fill: "#111827", font: { name: "Aptos Display", size: 10, bold: true, color: "#F8FAFC" }, rowHeight: 26 };
  used.format.autofitColumns();
  for (let column = 0; column < dataset.headers.length; column += 1) {
    const columnRange = sheet.getRangeByIndexes(0, column, dataset.rows.length + 1, 1);
    if (columnRange.format.columnWidth > 28) columnRange.format.columnWidth = 28;
  }
  if (dataset.sheet === "Sales") {
    [13, 16, 10, 11, 12, 22, 28].forEach((width, column) => { sheet.getRangeByIndexes(0, column, dataset.rows.length + 1, 1).format.columnWidth = width; });
    sheet.getRange(`A2:A${dataset.rows.length + 1}`).setNumberFormat("yyyy-mm-dd");
    sheet.getRange(`B2:B${dataset.rows.length + 1}`).setNumberFormat("$#,##0.00");
    sheet.getRange(`C2:D${dataset.rows.length + 1}`).setNumberFormat("#,##0");
  }
  if (dataset.sheet === "HR") {
    [32, 20, 9, 24, 13].forEach((width, column) => { sheet.getRangeByIndexes(0, column, dataset.rows.length + 1, 1).format.columnWidth = width; });
    sheet.getRange(`C2:C${dataset.rows.length + 1}`).setNumberFormat("#,##0");
    sheet.getRange(`E2:E${dataset.rows.length + 1}`).setNumberFormat("yyyy-mm-dd");
  }
  if (dataset.sheet === "Support") {
    [16, 30, 12, 12, 13].forEach((width, column) => { sheet.getRangeByIndexes(0, column, dataset.rows.length + 1, 1).format.columnWidth = width; });
  }
}

const inspection = await workbook.inspect({ kind: "sheet,table", maxChars: 4000, tableMaxRows: 5, tableMaxCols: 8 });
console.log(inspection.ndjson);
for (const dataset of datasets) {
  const preview = await workbook.render({ sheetName: dataset.sheet, range: `A1:${dataset.sheet === "Sales" ? "G" : "E"}12`, scale: 1.5, format: "png" });
  await fs.writeFile(path.join(outputDir, `${dataset.sheet}-preview.png`), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "Sentinel-Business-Data.xlsx"));

console.log(JSON.stringify({ sales: salesRows.length, support: supportRows.length, hr: hrRows.length, outputDir }));
