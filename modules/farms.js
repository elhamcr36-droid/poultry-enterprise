const express = require("express");
const router = express.Router();
const pool = require("../db");

router.get("/", async(req,res)=>{
const result = await pool.query("SELECT * FROM farms");
res.json(result.rows);
});

router.post("/", async(req,res)=>{
const {name,location} = req.body;

const result = await pool.query(
"INSERT INTO farms(name,location) VALUES($1,$2) RETURNING *",
[name,location]
);

res.json(result.rows[0]);
});

module.exports = router;
