const express = require("express");
const router = express.Router();

router.post("/login",(req,res)=>{

const {username,password} = req.body;

if(username==="admin" && password==="1234"){
return res.json({status:"ok"});
}

res.status(401).json({error:"invalid login"});

});

module.exports = router;
