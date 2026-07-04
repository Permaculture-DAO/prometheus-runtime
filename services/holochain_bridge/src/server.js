import express from 'express';
import { AdminWebsocket } from '@holochain/client';
const app=express();
const port=Number(process.env.BRIDGE_PORT || 8090);
const enabled=(process.env.HOLOCHAIN_ENABLED || 'false').toLowerCase()==='true';
const adminUrl=process.env.HOLOCHAIN_ADMIN_URL || 'ws://holochain-conductor:65000';
app.get('/health',async (_req,res)=>{
  if(!enabled) return res.status(200).json({status:'disabled',authoritative:false,statement:'evaluation, not certification'});
  try{const ws=await AdminWebsocket.connect({url:new URL(adminUrl),wsClientOptions:{origin:'prometheus-runtime'}});await ws.client.close();res.json({status:'ready',authoritative:false,statement:'evaluation, not certification'});}catch(e){res.status(503).json({status:'not-ready',error:String(e),authoritative:false});}
});
app.listen(port,'0.0.0.0',()=>console.log(`Holochain bridge on ${port}; enabled=${enabled}`));
