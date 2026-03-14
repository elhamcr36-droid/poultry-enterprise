const express = require("express");
const cors = require("cors");

const auth = require("./modules/auth");
const farms = require("./modules/farms");

const app = express();

app.use(cors());
app.use(express.json());

app.use("/auth", auth);
app.use("/farms", farms);

app.get("/", (req,res)=>{
res.json({message:"Poultry Enterprise API"});
});

app.get("/test-db", async(req,res)=>{
const pool = require("./db");
const result = await pool.query("SELECT NOW()");
res.json(result.rows);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT,()=>{
console.log("Server running on port",PORT);
});
