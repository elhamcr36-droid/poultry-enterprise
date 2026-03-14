const express = require("express");
const { Pool } = require("pg");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

// ใช้ DATABASE_URL จาก Render
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  }
});


// ---------------------
// Test Server
// ---------------------
app.get("/", (req, res) => {
  res.send("Poultry Enterprise API Running");
});


// ---------------------
// Test Database
// ---------------------
app.get("/test-db", async (req, res) => {
  try {
    const result = await pool.query("SELECT NOW()");
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).send("Database Error");
  }
});


// ---------------------
// GET chickens
// ---------------------
app.get("/chickens", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM chickens ORDER BY id DESC"
    );
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).send("Server Error");
  }
});


// ---------------------
// ADD chickens
// ---------------------
app.post("/chickens", async (req, res) => {
  try {
    const { house, total } = req.body;

    const result = await pool.query(
      "INSERT INTO chickens (house,total) VALUES ($1,$2) RETURNING *",
      [house, total]
    );

    res.json(result.rows[0]);
  } catch (err) {
    console.error(err);
    res.status(500).send("Insert Error");
  }
});


// ---------------------
// Delete chickens
// ---------------------
app.delete("/chickens/:id", async (req, res) => {
  try {
    const id = req.params.id;

    await pool.query("DELETE FROM chickens WHERE id=$1", [id]);

    res.json({ message: "Deleted" });
  } catch (err) {
    console.error(err);
    res.status(500).send("Delete Error");
  }
});


// ---------------------
// PORT
// ---------------------
const PORT = process.env.PORT || 3000;
async function createTable() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS chickens (
        id SERIAL PRIMARY KEY,
        house TEXT,
        total INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `)

    console.log("Table chickens ready")
  } catch (err) {
    console.error(err)
  }
}

createTable()

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
