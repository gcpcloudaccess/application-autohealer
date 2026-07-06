const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const url = require("url");

const PORT = process.env.PORT || 8000;
const PUBLIC_DIR = path.join(__dirname, "public");
const DATA_DIR = path.join(__dirname, "data");
const RECORDS_FILE = path.join(DATA_DIR, "records.json");
const MAX_NOTES_LENGTH = 2000;

const MIME_TYPES = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".jsx": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".ico": "image/x-icon",
};

function readRecords() {
  try {
    const raw = fs.readFileSync(RECORDS_FILE, "utf-8");
    return JSON.parse(raw);
  } catch (e) {
    return [];
  }
}

function writeRecords(records) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(RECORDS_FILE, JSON.stringify(records, null, 2), "utf-8");
}

function sendJSON(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(body);
}

function readBody(req, callback) {
  let data = "";
  req.on("data", (chunk) => {
    data += chunk;
    if (data.length > 1e6) {
      req.destroy();
    }
  });
  req.on("end", () => {
    if (!data) return callback(null, {});
    try {
      callback(null, JSON.parse(data));
    } catch (e) {
      callback(e);
    }
  });
}

function validateRecord(input) {
  const errors = [];
  const name = (input.name || "").toString().trim();
  const dob = (input.dob || "").toString().trim();
  const jobTitle = (input.jobTitle || "").toString().trim();
  const notes = (input.notes || "").toString();

  if (!name) errors.push("Name is required.");
  if (!dob) errors.push("Date of birth is required.");
  else if (Number.isNaN(Date.parse(dob))) errors.push("Date of birth is not a valid date.");
  if (!jobTitle) errors.push("Job title is required.");
  if (notes.length > MAX_NOTES_LENGTH) errors.push(`Notes must be ${MAX_NOTES_LENGTH} characters or fewer.`);

  return { errors, value: { name, dob, jobTitle, notes } };
}

function serveStatic(req, res) {
  const parsed = url.parse(req.url);
  let filePath = parsed.pathname === "/" ? "/index.html" : parsed.pathname;
  filePath = path.join(PUBLIC_DIR, path.normalize(filePath).replace(/^(\.\.[\/\\])+/, ""));

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === "ENOENT") {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("Not found");
      } else {
        res.writeHead(500, { "Content-Type": "text/plain" });
        res.end("Server error");
      }
      return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
    res.end(content);
  });
}

function handleApi(req, res, pathname) {
  if (pathname === "/health") {
    return sendJSON(res, 200, { status: "ok", service: "backend" });
  }

  if (pathname === "/api/status") {
    return sendJSON(res, 200, { message: "Backend is running", version: "2.0.0" });
  }

  if (pathname === "/api/records" && req.method === "GET") {
    return sendJSON(res, 200, readRecords());
  }

  if (pathname === "/api/records" && req.method === "POST") {
    return readBody(req, (err, body) => {
      if (err) return sendJSON(res, 400, { error: "Invalid JSON body." });
      const { errors, value } = validateRecord(body);
      if (errors.length) return sendJSON(res, 400, { error: errors.join(" ") });

      const records = readRecords();
      const record = {
        id: crypto.randomUUID(),
        name: value.name,
        dob: value.dob,
        jobTitle: value.jobTitle,
        notes: value.notes,
        createdAt: new Date().toISOString(),
      };
      records.push(record);
      writeRecords(records);
      return sendJSON(res, 201, record);
    });
  }

  const deleteMatch = pathname.match(/^\/api\/records\/([^/]+)$/);
  if (deleteMatch && req.method === "DELETE") {
    const id = decodeURIComponent(deleteMatch[1]);
    const records = readRecords();
    const index = records.findIndex((r) => r.id === id);
    if (index === -1) return sendJSON(res, 404, { error: "Record not found." });
    records.splice(index, 1);
    writeRecords(records);
    return sendJSON(res, 200, { success: true });
  }

  return sendJSON(res, 404, { error: "Not found." });
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url);
  const pathname = parsed.pathname;

  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    });
    return res.end();
  }

  if (pathname === "/health" || pathname.startsWith("/api/")) {
    return handleApi(req, res, pathname);
  }

  return serveStatic(req, res);
});

server.listen(PORT, () => {
  console.log(`Backend admin app listening on port ${PORT}`);
});
