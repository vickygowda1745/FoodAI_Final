import os, io, re, json, math, time, base64, threading
from datetime import datetime
import requests
from PIL import Image
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL","qwen3-vl:4b")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID","").strip()
RADIUS = int(os.getenv("RESTAURANT_RADIUS_METERS","12000"))
MODEL_LOCK = threading.Lock()
CACHE = {}

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#07100b">
<title>FoodAI</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{--g:#58ef97;--o:#ff9d37;--bg:#050806;--card:rgba(13,24,18,.78);--muted:#9ba89f;--line:rgba(118,255,169,.18)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-height:100vh;color:#f7faf8;background:radial-gradient(circle at 10% 10%,rgba(33,143,79,.25),transparent 30%),radial-gradient(circle at 92% 25%,rgba(255,146,42,.14),transparent 28%),linear-gradient(155deg,#030504,#08110c 50%,#030504);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}
body:before,body:after{content:"";position:fixed;border-radius:999px;filter:blur(100px);opacity:.22;pointer-events:none}body:before{width:260px;height:260px;background:#1dce70;left:-120px;top:18%}body:after{width:260px;height:260px;background:#ff8528;right:-120px;bottom:12%}
.app{width:min(100%,1120px);margin:auto;padding:max(14px,env(safe-area-inset-top)) 14px 105px;position:relative;z-index:1}
header{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:14px}.brand{display:flex;align-items:center;gap:12px}.logo{width:52px;height:52px;border-radius:18px;background:linear-gradient(145deg,#183326,#0a120d);border:1px solid rgba(88,239,151,.35);display:grid;place-items:center;font-size:27px;box-shadow:inset 0 0 28px rgba(88,239,151,.08)}h1{font-size:30px;letter-spacing:-1.3px;margin:0}.brand h1 span{color:var(--g)}.brand p{margin:4px 0 0;color:var(--muted);font-size:12px}.status{text-align:right}.pill{display:inline-flex;align-items:center;gap:8px;padding:9px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(11,31,20,.7);font-size:11px}.dot{width:8px;height:8px;border-radius:50%;background:var(--g);box-shadow:0 0 12px var(--g)}#tgStatus{display:block;color:#819086;font-size:10px;margin-top:6px}
.camera{height:min(78vh,800px);min-height:600px;position:relative;overflow:hidden;border-radius:34px;border:1px solid rgba(112,255,163,.22);background:#07100b;box-shadow:0 28px 80px rgba(0,0,0,.46)}
video{width:100%;height:100%;object-fit:cover;background:#07100b}.vignette{position:absolute;inset:0;pointer-events:none;background:linear-gradient(to bottom,rgba(3,8,5,.74),transparent 22%,transparent 63%,rgba(3,7,5,.88))}
.ready{position:absolute;top:30px;left:50%;transform:translateX(-50%);padding:10px 17px;border-radius:999px;background:rgba(7,28,17,.76);border:1px solid rgba(90,239,145,.35);backdrop-filter:blur(18px);white-space:nowrap;font-size:13px}.ready b{color:var(--g)}
.hint{position:absolute;top:79px;left:0;right:0;text-align:center;color:rgba(255,255,255,.7);font-size:12px}
.focus{position:absolute;width:min(82%,660px);aspect-ratio:1.18;left:50%;top:46%;transform:translate(-50%,-50%)}.c{position:absolute;width:62px;height:62px;filter:drop-shadow(0 0 10px rgba(84,255,147,.45))}.tl{left:0;top:0;border-left:5px solid #d9ffe5;border-top:5px solid #d9ffe5;border-radius:24px 0 0}.tr{right:0;top:0;border-right:5px solid #d9ffe5;border-top:5px solid #d9ffe5;border-radius:0 24px 0 0}.bl{left:0;bottom:0;border-left:5px solid #d9ffe5;border-bottom:5px solid #d9ffe5;border-radius:0 0 0 24px}.br{right:0;bottom:0;border-right:5px solid #d9ffe5;border-bottom:5px solid #d9ffe5;border-radius:0 0 24px}.beam{height:3px;position:absolute;left:18px;right:18px;top:14%;opacity:0;background:linear-gradient(90deg,transparent,#57ef98,#f0fff5,#57ef98,transparent);box-shadow:0 0 20px rgba(74,255,139,.8)}.camera.scanning .beam{opacity:1;animation:scan 1.35s ease-in-out infinite}@keyframes scan{0%,100%{top:12%}50%{top:84%}}
.work{position:absolute;left:50%;bottom:145px;transform:translateX(-50%);display:flex;align-items:center;gap:12px;background:rgba(5,13,8,.88);border:1px solid var(--line);border-radius:20px;padding:12px 17px;backdrop-filter:blur(18px);min-width:230px}.spinner{width:31px;height:31px;border-radius:50%;border:3px solid rgba(88,239,151,.16);border-top-color:var(--g);animation:spin .7s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.work small{display:block;color:var(--muted);margin-top:3px}
.controls{position:absolute;left:0;right:0;bottom:24px;display:flex;align-items:center;justify-content:center;gap:28px}.circle{width:68px;height:68px;border-radius:50%;border:1px solid rgba(255,255,255,.16);background:rgba(7,12,9,.72);color:#fff;backdrop-filter:blur(18px);font-size:22px}.scanbtn{width:128px;height:128px;border-radius:50%;border:5px solid #492b14;outline:2px solid rgba(255,180,78,.72);background:radial-gradient(circle at 34% 22%,#ffd069,#ff9d37 48%,#ff7525);color:#fff;box-shadow:0 14px 48px rgba(255,126,31,.34);font-weight:800}.scanbtn span{display:block;font-size:30px;margin-bottom:5px}
.privacy{max-width:760px;margin:14px auto 0;color:#87938b;font-size:10px;line-height:1.45;text-align:center}
.hidden{display:none!important}.title{display:flex;align-items:center;gap:12px;margin:8px 0 20px}.back{width:46px;height:46px;border-radius:50%;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#fff;font-size:28px}.eyebrow{font-size:10px;letter-spacing:1.5px;color:var(--g);font-weight:800}.title h2{margin:4px 0 0}
.hero{display:grid;grid-template-columns:minmax(260px,.85fr) minmax(320px,1.15fr);gap:20px;padding:18px;border-radius:30px;border:1px solid rgba(88,239,151,.26);background:linear-gradient(135deg,rgba(18,51,31,.68),rgba(8,13,10,.87));box-shadow:0 28px 80px rgba(0,0,0,.38)}.hero>img{width:100%;height:340px;object-fit:cover;border-radius:22px}.badge{display:inline-flex;padding:7px 11px;border-radius:999px;background:rgba(74,234,132,.12);border:1px solid rgba(74,234,132,.22);color:#adf8c6;font-size:11px}.hero h2{font-size:clamp(34px,6vw,58px);line-height:.98;letter-spacing:-2px;margin:16px 0}.conf{display:flex;justify-content:space-between;color:#c8d0cb;font-size:13px}.conf b{color:var(--g)}.bar{height:9px;border-radius:999px;background:rgba(255,255,255,.09);overflow:hidden;margin:8px 0 14px}.bar div{height:100%;background:linear-gradient(90deg,#25d66a,#70ffa2)}.desc{color:#d8dedb;line-height:1.55}.reason{color:#87938b;font-size:11px;line-height:1.45}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.tag{font-size:11px;padding:7px 11px;border-radius:999px}.tag.o{background:rgba(255,147,42,.1);color:#ffc887}.tag.g{background:rgba(67,237,128,.1);color:#a8f8c2}
.nutrition{margin-top:18px;padding:18px;border-radius:26px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03)}.sectionhead{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:13px}.sectionhead h3{margin:3px 0 0;font-size:24px}.sectionhead p{margin:0;color:#829087;font-size:10px;text-align:right}.macros{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.macro{padding:14px 10px;border-radius:18px;background:linear-gradient(145deg,rgba(27,43,34,.9),rgba(8,13,10,.94));border:1px solid rgba(255,255,255,.07);text-align:center}.macro b{display:block;font-size:23px}.macro small{color:#8c9991}.serving{margin-top:10px;color:#9ea9a2;font-size:11px}
.warn{max-width:760px;margin:auto;padding:22px;border-radius:30px;border:1px solid rgba(255,190,70,.3);background:linear-gradient(145deg,rgba(67,46,17,.38),rgba(8,13,10,.92));text-align:center}.warnicon{width:50px;height:50px;border-radius:50%;display:grid;place-items:center;margin:0 auto 12px;background:#ffbf48;color:#181005;font-weight:900;font-size:24px}.warn img{width:100%;height:280px;object-fit:cover;border-radius:22px;margin:14px 0}.cands{display:grid;gap:9px}.cand{display:flex;justify-content:space-between;align-items:center;padding:13px 14px;border-radius:16px;background:rgba(255,255,255,.035);text-align:left}.cand span:last-child{color:#ffc366;font-weight:800}.retry{margin-top:14px;padding:13px 18px;border-radius:16px;border:0;background:linear-gradient(135deg,#ffc95f,#ff8b29);font-weight:800;color:#251506}
.near{margin-top:30px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.rest{padding:17px;border-radius:22px;background:linear-gradient(145deg,rgba(25,39,31,.93),rgba(8,13,10,.96));border:1px solid rgba(255,255,255,.08)}.rest h4{margin:12px 0 5px;font-size:17px}.rest p{margin:0 0 12px;color:#929e96;font-size:11px;line-height:1.5}.distance{color:var(--g);font-weight:800}.navbtn{width:100%;height:40px;border-radius:13px;border:1px solid rgba(88,239,151,.24);background:rgba(88,239,151,.08);color:#caffdc}.mapwrap{overflow:hidden;border-radius:25px;border:1px solid rgba(88,239,151,.18);margin-top:14px}#map{height:350px;background:#101a13}.mapnote{padding:9px 12px;text-align:center;color:#78867d;font-size:9px}.another{display:block;margin:22px auto 0;padding:13px 22px;border-radius:17px;border:1px solid rgba(255,157,55,.3);background:rgba(255,157,55,.08);color:#ffd19a}
nav{position:fixed;z-index:999;left:50%;bottom:max(14px,env(safe-area-inset-bottom));transform:translateX(-50%);width:min(calc(100% - 28px),450px);height:68px;padding:7px;display:flex;justify-content:space-around;border-radius:24px;border:1px solid rgba(255,255,255,.1);background:rgba(7,12,9,.88);backdrop-filter:blur(24px)}nav button{width:31%;border:0;border-radius:16px;background:transparent;color:#78847c}nav button.active{background:rgba(88,239,151,.08);color:var(--g)}nav span,nav small{display:block}.toast{position:fixed;left:50%;bottom:95px;transform:translate(-50%,18px);padding:11px 15px;border-radius:14px;background:rgba(5,12,8,.95);border:1px solid rgba(255,255,255,.1);opacity:0;transition:.2s;z-index:2000;max-width:calc(100% - 30px);text-align:center}.toast.show{opacity:1;transform:translate(-50%,0)}
@media(max-width:760px){.app{padding:10px 9px 100px}.brand p{display:none}.status{max-width:140px}.pill{font-size:9px;padding:8px 9px}.camera{height:calc(100svh - 150px);min-height:570px;border-radius:29px}.focus{width:87%;top:44%;aspect-ratio:1}.controls{gap:18px}.circle{width:61px;height:61px}.scanbtn{width:114px;height:114px}.work{bottom:132px}.hero{grid-template-columns:1fr;padding:13px}.hero>img{height:260px}.macros{grid-template-columns:repeat(2,1fr)}.macro:first-child{grid-column:span 2}.cards{display:flex;overflow-x:auto}.rest{min-width:82%}#map{height:300px}.sectionhead{align-items:flex-start;flex-direction:column}.sectionhead p{text-align:left}}
</style>
</head>
<body>
<div class="app">
<header><div class="brand"><div class="logo">🍃</div><div><h1>Food<span>AI</span></h1><p>Food Recognition & Recommendations</p></div></div><div class="status"><div class="pill"><span class="dot"></span><span id="locText">Getting location…</span></div><span id="tgStatus">Telegram checking…</span></div></header>

<section id="scanner">
<div id="cameraBox" class="camera">
<video id="video" autoplay playsinline muted></video><canvas id="canvas" class="hidden"></canvas><div class="vignette"></div>
<div class="ready">⌁ <b id="aiState">AI Ready</b></div><div class="hint">Point your rear camera at one food dish</div>
<div class="focus"><i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i><div class="beam"></div></div>
<div id="working" class="work hidden"><div class="spinner"></div><div><strong>AI analyzing…</strong><small>Recognizing food + nutrition</small></div></div>
<div class="controls"><button id="flip" class="circle">↻</button><button id="scan" class="scanbtn"><span>◉</span>Scan Food</button><button id="gps" class="circle">⌖</button></div>
</div>
<div class="privacy">🔒 Camera frames are analyzed by the local AI model. Location is used for nearby restaurants. If Telegram is connected, the scan photo and location are sent to your bot.</div>
</section>

<section id="results" class="hidden">
<div class="title"><button id="back" class="back">‹</button><div><div class="eyebrow">RECOGNITION RESULT</div><h2>Here's what FoodAI found</h2></div></div>

<div id="good" class="hidden">
<div class="hero"><img id="foodImg"><div><span class="badge">✓ Food Recognized</span><h2 id="foodName"></h2><div class="conf"><span>AI confidence</span><b id="confText"></b></div><div class="bar"><div id="confBar"></div></div><div class="tags"><span id="cuisine" class="tag o"></span><span class="tag g">Local AI</span></div><p id="desc" class="desc"></p><p id="why" class="reason"></p></div></div>
<div class="nutrition"><div class="sectionhead"><div><div class="eyebrow">ESTIMATED NUTRITION</div><h3>Typical serving</h3></div><p>Photo-based estimate — actual recipe and portion can vary.</p></div><div class="macros"><div class="macro"><b id="cal">—</b><small>Calories</small></div><div class="macro"><b id="protein">—</b><small>Protein</small></div><div class="macro"><b id="carbs">—</b><small>Carbs</small></div><div class="macro"><b id="fat">—</b><small>Fat</small></div><div class="macro"><b id="fiber">—</b><small>Fiber</small></div></div><div id="serving" class="serving"></div></div>
</div>

<div id="uncertain" class="warn hidden"><div class="warnicon">!</div><div class="eyebrow" style="color:#ffc05d">LOW CONFIDENCE</div><h2>Needs Another Angle</h2><p style="color:#9fa9a3">FoodAI won't confidently show a dish name when the image is ambiguous.</p><img id="uncertainImg"><div id="candList" class="cands"></div><button id="retry" class="retry">↻ Rescan Food</button></div>

<section class="near"><div class="sectionhead"><div><div class="eyebrow">NEAR YOU</div><h3>Nearby Restaurants</h3></div><p id="restStatus">Waiting for location…</p></div><div id="cards" class="cards"></div><div class="mapwrap"><div id="map"></div><div class="mapnote">Restaurant data from OpenStreetMap. Confirm menu availability with the restaurant.</div></div></section>
<button id="another" class="another">Scan Another Food</button>
</section>

<nav><button id="nScan" class="active"><span>⌂</span><small>Scan</small></button><button id="nResult"><span>✦</span><small>Result</small></button><button id="nNear"><span>⌖</span><small>Nearby</small></button></nav>
</div><div id="toast" class="toast"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const S={stream:null,facing:"environment",img:null,result:null,coords:null,map:null,markers:[],tg:false};const $=x=>document.getElementById(x);
function toast(m,d=2600){const t=$("toast");t.textContent=m;t.classList.add("show");clearTimeout(t._);t._=setTimeout(()=>t.classList.remove("show"),d)}
async function health(){try{const d=await(await fetch("/api/health")).json();$("aiState").textContent=d.ollama&&d.model_installed?"AI Ready":"AI Offline";S.tg=d.telegram_configured;$("tgStatus").textContent=S.tg?"✈ Telegram bot active":"Telegram not connected yet"}catch{$("aiState").textContent="Server error"}}
async function camera(){
  const v=$("video");
  try{
    if(!window.isSecureContext)throw new Error("Camera requires HTTPS.");
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)throw new Error("This browser does not provide camera access.");
    if(S.stream){S.stream.getTracks().forEach(t=>t.stop());S.stream=null}
    $("aiState").textContent="Starting camera…";

    const attempts=[
      {audio:false,video:{facingMode:{ideal:S.facing},width:{ideal:1280},height:{ideal:720}}},
      {audio:false,video:{facingMode:{ideal:S.facing}}},
      {audio:false,video:true}
    ];

    let stream=null,lastError=null;
    for(const constraints of attempts){
      try{stream=await navigator.mediaDevices.getUserMedia(constraints);break}
      catch(err){lastError=err;console.warn("Camera attempt failed:",err.name,err.message)}
    }
    if(!stream)throw lastError||new Error("Camera unavailable.");

    S.stream=stream;
    v.srcObject=stream;
    v.muted=true;
    v.setAttribute("playsinline","");
    await v.play();

    $("aiState").textContent="AI Ready";
    toast(S.facing==="environment"?"Rear camera ready ✅":"Camera ready ✅",2200);
    return true;
  }catch(e){
    console.error("CAMERA_ERROR:",e.name,e.message);
    S.stream=null;
    $("aiState").textContent="Camera not ready";

    let msg="Camera could not start.";
    if(e.name==="NotAllowedError"||e.name==="PermissionDeniedError")msg="Camera blocked. In Chrome, allow Camera for this site and reload.";
    else if(e.name==="NotFoundError"||e.name==="DevicesNotFoundError")msg="No camera was found on this device.";
    else if(e.name==="NotReadableError"||e.name==="TrackStartError")msg="Camera is busy. Close other camera apps and retry.";
    else if(e.name==="OverconstrainedError"||e.name==="ConstraintNotSatisfiedError")msg="Camera mode unsupported. FoodAI will retry with basic camera mode.";
    else if(e.message)msg=e.message;

    toast(msg,6500);
    return false;
  }
}
async function gps(show=false){if(!navigator.geolocation){$("locText").textContent="GPS unavailable";return null}$("locText").textContent="Finding location…";return new Promise(r=>navigator.geolocation.getCurrentPosition(p=>{S.coords={lat:p.coords.latitude,lon:p.coords.longitude,accuracy:p.coords.accuracy};$("locText").textContent="Location On";if(show)toast("Location ready");r(S.coords)},()=>{$("locText").textContent="Location Off";S.coords=null;if(show)toast("Location permission was not available.",4000);r(null)},{enableHighAccuracy:true,timeout:8000,maximumAge:60000}))}
function capture(){const v=$("video"),c=$("canvas"),w=v.videoWidth,h=v.videoHeight;if(!w||!h)throw Error("Camera is not ready yet.");const cw=w*.86,ch=h*.70,sx=(w-cw)/2,sy=(h-ch)/2,ratio=Math.min(1,960/cw);c.width=Math.round(cw*ratio);c.height=Math.round(ch*ratio);c.getContext("2d").drawImage(v,sx,sy,cw,ch,0,0,c.width,c.height);return c.toDataURL("image/jpeg",.8)}
function loading(on){$("scan").disabled=on;$("cameraBox").classList.toggle("scanning",on);$("working").classList.toggle("hidden",!on);$("aiState").textContent=on?"Vision AI Working":"AI Ready"}
function showResults(){$("scanner").classList.add("hidden");$("results").classList.remove("hidden");$("nScan").classList.remove("active");$("nResult").classList.add("active");window.scrollTo({top:0,behavior:"smooth"})}
function showScanner(){$("results").classList.add("hidden");$("scanner").classList.remove("hidden");$("nResult").classList.remove("active");$("nNear").classList.remove("active");$("nScan").classList.add("active");window.scrollTo({top:0,behavior:"smooth"})}
function safe(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;")}
function render(r){S.result=r;showResults();if(r.needs_rescan||!r.is_food){$("good").classList.add("hidden");$("uncertain").classList.remove("hidden");$("uncertainImg").src=S.img;const a=[{name:r.food_name,confidence:r.confidence},...(r.alternatives||[])].slice(0,3);$("candList").innerHTML=a.map(x=>`<div class="cand"><span>${safe(x.name)}</span><span>${Math.round(Number(x.confidence)||0)}%</span></div>`).join("")}else{$("uncertain").classList.add("hidden");$("good").classList.remove("hidden");$("foodImg").src=S.img;$("foodName").textContent=r.food_name;$("confText").textContent=r.confidence+"%";$("confBar").style.width=r.confidence+"%";$("cuisine").textContent=r.cuisine||"Cuisine";$("desc").textContent=r.description||"";$("why").textContent=r.reason?"Why: "+r.reason:"";const n=r.nutrition||{};$("cal").textContent=(n.calories??"—")+" kcal";$("protein").textContent=(n.protein_g??"—")+" g";$("carbs").textContent=(n.carbs_g??"—")+" g";$("fat").textContent=(n.fat_g??"—")+" g";$("fiber").textContent=(n.fiber_g??"—")+" g";$("serving").textContent=n.serving_estimate?"Estimated serving: "+n.serving_estimate:""}}
async function getRestaurants(){if(!S.coords){$("restStatus").textContent="Location required";return}try{$("restStatus").textContent="Finding nearby places…";const d=await(await fetch("/api/restaurants",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(S.coords)})).json();if(!d.ok)throw Error(d.error||"Lookup failed");$("restStatus").textContent=d.restaurants.length+" nearby";cards(d.restaurants);map(d.restaurants)}catch(e){console.error(e);$("restStatus").textContent="Restaurant service delayed"}}
function cards(rs){$("cards").innerHTML=rs.slice(0,6).map(p=>`<article class="rest"><div>🍽</div><h4>${safe(p.name)}</h4><p><span class="distance">${Number(p.distance_km).toFixed(1)} km</span><br>${safe(p.cuisine)}<br>${safe(p.address)}</p><button class="navbtn" data-lat="${p.lat}" data-lon="${p.lon}">➤ Navigate</button></article>`).join("");document.querySelectorAll(".navbtn").forEach(b=>b.onclick=()=>window.open("https://www.google.com/maps/dir/?api=1&destination="+encodeURIComponent(b.dataset.lat+","+b.dataset.lon),"_blank","noopener"))}
function map(rs){if(!S.coords||typeof L==="undefined")return;if(!S.map){S.map=L.map("map").setView([S.coords.lat,S.coords.lon],14);L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap contributors"}).addTo(S.map)}S.markers.forEach(m=>m.remove());S.markers=[];S.markers.push(L.circleMarker([S.coords.lat,S.coords.lon],{radius:9,weight:4,color:"#fff",fillColor:"#318bff",fillOpacity:1}).addTo(S.map).bindPopup("Your location"));rs.slice(0,10).forEach(p=>S.markers.push(L.marker([p.lat,p.lon]).addTo(S.map).bindPopup("<b>"+safe(p.name)+"</b><br>"+Number(p.distance_km).toFixed(1)+" km")));const pts=[[S.coords.lat,S.coords.lon],...rs.slice(0,7).map(p=>[p.lat,p.lon])];if(pts.length>1)S.map.fitBounds(pts,{padding:[35,35],maxZoom:14});setTimeout(()=>S.map.invalidateSize(),250)}
async function notify(){if(!S.tg||!S.img||!S.result)return;try{$("tgStatus").textContent="✈ Sending Telegram…";const d=await(await fetch("/api/notify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({image:S.img,recognition:S.result,lat:S.coords?.lat??null,lon:S.coords?.lon??null})})).json();$("tgStatus").textContent=d.sent?"✓ Telegram sent":"Telegram not connected"}catch{$("tgStatus").textContent="Telegram send failed"}}
async function doScan(){
  if(!S.stream){
    const ok=await camera();
    if(!ok)return;
    toast("Camera ready — point at the food and tap Scan.",3200);
    return;
  }
  try{
    loading(true);
    S.img=capture();
    const rp=S.coords?getRestaurants():Promise.resolve();
    const response=await fetch("/api/recognize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({image:S.img})});
    const d=await response.json();
    if(!response.ok||!d.ok)throw Error(d.error||"Recognition failed");
    render(d);
    toast("Recognition completed in "+d.latency_seconds+"s");
    rp.catch(console.error);
    notify();
  }catch(e){
    console.error(e);
    toast(e.message||"Recognition failed",5000);
  }finally{
    loading(false);
  }
}
$("scan").onclick=doScan;$("flip").onclick=async()=>{S.facing=S.facing==="environment"?"user":"environment";await camera()};$("gps").onclick=async()=>{await gps(true);if(S.coords)getRestaurants()};$("back").onclick=showScanner;$("retry").onclick=showScanner;$("another").onclick=showScanner;$("nScan").onclick=showScanner;$("nResult").onclick=()=>S.result?showResults():toast("Scan a food first.");$("nNear").onclick=()=>{if($("results").classList.contains("hidden"))return toast("Scan a food first.");document.querySelector(".near").scrollIntoView({behavior:"smooth"});setTimeout(()=>S.map&&S.map.invalidateSize(),500)};
(async()=>{await health();const camOK=await camera();if(!camOK)$("aiState").textContent="Tap Scan to start camera";await gps(false);if(S.coords)getRestaurants()})();
</script>
</body></html>'''

def clamp(v,a,b):
    try: return max(a,min(b,float(v)))
    except: return a

def clean_json(text):
    text=(text or "").strip()
    text=re.sub(r"^```json\s*","",text,flags=re.I)
    text=re.sub(r"^```\s*","",text)
    text=re.sub(r"\s*```$","",text)
    try: return json.loads(text)
    except: pass
    a,b=text.find("{"),text.rfind("}")
    if a>=0 and b>a: return json.loads(text[a:b+1])
    raise ValueError("Vision model returned invalid JSON.")

def prepare_image(data):
    if "," in data: data=data.split(",",1)[1]
    raw=base64.b64decode(data)
    im=Image.open(io.BytesIO(raw)).convert("RGB")
    w,h=im.size
    mx=1024
    if max(w,h)>mx:
        s=mx/max(w,h); im=im.resize((int(w*s),int(h*s)),Image.Resampling.LANCZOS)
    out=io.BytesIO(); im.save(out,"JPEG",quality=70,optimize=True)
    return base64.b64encode(out.getvalue()).decode(),out.getvalue()

def ask_vision(prompt,img,timeout=90):
    payload={"model":OLLAMA_MODEL,"messages":[{"role":"user","content":prompt,"images":[img]}],"stream":False,"format":"json","think":False,"keep_alive":-1,"options":{"temperature":0.05,"top_p":0.85,"num_ctx":4096,"num_predict":650}}
    with MODEL_LOCK:
        r=requests.post(f"{OLLAMA_URL}/api/chat",json=payload,timeout=timeout)
    r.raise_for_status()
    return clean_json(r.json().get("message",{}).get("content",""))

def recognize(img):
    prompt = (
        "You are FoodAI, an OPEN-WORLD visual food recognition system for foods from anywhere in the world.\n"
        "There is NO fixed class list. Identify the food shown in this single image using visual evidence only.\n"
        "Do not assume a common Indian dish, a previous scan, or any example in this prompt.\n\n"

        "RECOGNITION PROCEDURE:\n"
        "1. First determine whether the image actually contains food or a drink.\n"
        "2. Determine the broad visual food family before naming the exact dish: for example rice dish, flatbread/crepe/pancake, bread, curry/stew, soup, noodles/pasta, fried snack, grilled/roasted item, salad, dessert, bakery item, fruit, beverage, or another visually appropriate family.\n"
        "3. Inspect shape, thickness, texture, crispness, grain/noodle/bread structure, sauce consistency, cooking style, visible ingredients, garnish, filling, and visible protein.\n"
        "4. Only then choose the most specific dish name that the image supports.\n"
        "5. If the exact regional dish is uncertain, use a broader truthful name and put plausible exact dishes in alternatives. Never force the image into a familiar class.\n\n"

        "ANTI-CONFUSION RULES:\n"
        "- A thin round or folded fermented crepe-like South Indian food should be considered dosa-type food, not a rice dish merely because of color or plate presentation.\n"
        "- Rice grains must actually be visible before calling something biryani, pulao, fried rice, or another rice dish.\n"
        "- Noodles/pasta strands must actually be visible before using a noodle or pasta name.\n"
        "- Bread, roti, naan, tortilla, dosa, pancake, crepe and similar flat foods must be distinguished from rice dishes by structure and texture.\n"
        "- Do not identify a meat/protein subtype unless that protein is visually supported.\n"
        "- For biryani, never default to chicken: use Prawn Biryani only for visible prawns/shrimp, Mutton Biryani only for visible mutton/goat/lamb, Chicken Biryani only for visible chicken, Egg Biryani for visible egg-dominant biryani, Vegetable Biryani when vegetables are dominant with no visible meat, otherwise simply Biryani.\n"
        "- Do not decide cuisine from plate color, table, restaurant setting, or geography alone.\n\n"

        "WORLDWIDE COVERAGE:\n"
        "Recognize foods from South Asian, East Asian, Southeast Asian, Middle Eastern, African, European, Mediterranean, North American, Latin American and other regional cuisines. "
        "Also recognize snacks, street foods, sweets, desserts, bakery foods, fruits, vegetables and drinks. "
        "If a dish is unfamiliar or visually ambiguous, say so through lower confidence and alternatives instead of inventing a confident label.\n\n"

        "CONFIDENCE:\n"
        "- Use high confidence only when distinctive visual evidence supports the exact dish.\n"
        "- Lower confidence when several dishes look similar or important ingredients are hidden.\n"
        "- alternatives should contain up to 3 genuinely plausible alternatives, each with its own confidence.\n"
        "- The reason must be a short user-facing visual explanation, not hidden reasoning.\n\n"

        "Return ONLY valid JSON with exactly these top-level keys: "
        "is_food, food_name, confidence, cuisine, description, reason, alternatives, nutrition.\n"
        "is_food must be true or false. confidence must be 0-100.\n"
        "food_name must be the best visually supported name, not a forced guess.\n"
        "cuisine may be Unknown when cuisine cannot be reliably inferred.\n"
        "alternatives must be a JSON list of objects with name and confidence.\n"
        "nutrition must contain serving_estimate, calories, protein_g, carbs_g, fat_g, fiber_g.\n"
        "Nutrition is a rough typical-serving estimate, not a measurement from the photograph. "
        "If nutrition is uncertain, zeros are allowed because FoodAI supplies a local fallback.\n"
        "Do not include markdown, commentary, code fences, or text outside the JSON object."
    )

    raw = ask_vision(prompt, img, timeout=60)

    if isinstance(raw, dict):
        d = raw
    else:
        parsed = clean_json(str(raw))
        if isinstance(parsed, dict):
            d = parsed
        else:
            import json as _json
            d = _json.loads(parsed)

    def _num(v, default=0.0):
        try:
            return float(v)
        except Exception:
            return float(default)

    def _nutrition_ok(n):
        if not isinstance(n, dict):
            return False
        vals = [_num(n.get(k, 0)) for k in ("calories","protein_g","carbs_g","fat_g","fiber_g")]
        return sum(v > 0 for v in vals) >= 3

    def _fallback_nutrition(food_name):
        name = (food_name or "").lower()
        profiles = [
            (("prawn biryani","prawns biryani","shrimp biryani"), "1 plate (~350 g)", 560, 26, 75, 18, 4),
            (("mutton biryani","goat biryani","lamb biryani"), "1 plate (~350 g)", 700, 30, 72, 30, 4),
            (("chicken biryani",), "1 plate (~350 g)", 620, 28, 78, 22, 4),
            (("egg biryani",), "1 plate (~350 g)", 520, 18, 78, 15, 4),
            (("vegetable biryani","veg biryani"), "1 plate (~350 g)", 480, 11, 82, 12, 6),
            (("biryani",), "1 plate (~350 g)", 560, 18, 80, 18, 5),
            (("fried rice",), "1 plate (~350 g)", 500, 13, 78, 15, 5),
            (("curd rice",), "1 bowl (~300 g)", 380, 10, 62, 10, 2),
            (("lemon rice",), "1 plate (~300 g)", 430, 8, 72, 13, 4),
            (("dosa",), "1 medium serving", 260, 6, 40, 8, 3),
            (("idli",), "3 idlis", 180, 6, 36, 1, 3),
            (("vada",), "2 pieces", 300, 9, 34, 15, 5),
            (("chapati","roti"), "2 medium pieces", 220, 7, 42, 4, 6),
            (("paneer",), "1 serving (~250 g)", 420, 20, 20, 28, 5),
            (("chicken curry",), "1 bowl (~250 g)", 420, 34, 15, 25, 3),
            (("fish curry",), "1 bowl (~250 g)", 360, 32, 12, 20, 3),
            (("dal","dhal"), "1 bowl (~250 g)", 300, 15, 42, 9, 12),
            (("pizza",), "2 medium slices", 520, 22, 62, 21, 5),
            (("burger",), "1 burger", 500, 24, 48, 24, 4),
            (("sandwich",), "1 sandwich", 360, 16, 44, 14, 5),
        ]
        for words, serving, cal, protein, carbs, fat, fiber in profiles:
            if any(w in name for w in words):
                return {
                    "serving_estimate": serving,
                    "calories": cal,
                    "protein_g": protein,
                    "carbs_g": carbs,
                    "fat_g": fat,
                    "fiber_g": fiber,
                }
        return {
            "serving_estimate": "1 typical serving (~250 g)",
            "calories": 350,
            "protein_g": 14,
            "carbs_g": 45,
            "fat_g": 12,
            "fiber_g": 5,
        }

    is_food = bool(d.get("is_food", True))
    name = str(d.get("food_name", "Unknown food")).strip() or "Unknown food"
    conf = int(round(clamp(_num(d.get("confidence", 0)), 0, 100)))
    reason = str(d.get("reason", "")).strip()

    low_reason = reason.lower()
    if "chicken biryani" in name.lower():
        chicken_evidence = any(x in low_reason for x in ("chicken", "drumstick", "poultry", "chicken piece", "chicken meat"))
        if not chicken_evidence and conf < 80:
            name = "Biryani"
            conf = min(conf, 68)

    alts = []
    src_alts = d.get("alternatives", [])
    if isinstance(src_alts, list):
        for a in src_alts[:3]:
            if isinstance(a, dict):
                an = str(a.get("name", "")).strip()
                if an:
                    alts.append({"name": an, "confidence": int(round(clamp(_num(a.get("confidence", 0)), 0, 100)))})
            elif isinstance(a, str) and a.strip():
                alts.append({"name": a.strip(), "confidence": max(1, conf - 12)})

    nutrition = d.get("nutrition", {})
    if not _nutrition_ok(nutrition):
        nutrition = _fallback_nutrition(name)
    else:
        nutrition = {
            "serving_estimate": str(nutrition.get("serving_estimate", "1 typical serving")),
            "calories": int(round(clamp(_num(nutrition.get("calories", 0)), 0, 2500))),
            "protein_g": round(clamp(_num(nutrition.get("protein_g", 0)), 0, 250), 1),
            "carbs_g": round(clamp(_num(nutrition.get("carbs_g", 0)), 0, 400), 1),
            "fat_g": round(clamp(_num(nutrition.get("fat_g", 0)), 0, 250), 1),
            "fiber_g": round(clamp(_num(nutrition.get("fiber_g", 0)), 0, 100), 1),
        }

    needs = (not is_food) or conf < 52

    return {
        "is_food": is_food,
        "food_name": name,
        "confidence": conf,
        "cuisine": str(d.get("cuisine", "Unknown")).strip() or "Unknown",
        "description": str(d.get("description", "")).strip(),
        "reason": reason,
        "needs_rescan": needs,
        "alternatives": alts,
        "nutrition": nutrition,
    }

def hav(lat1,lon1,lat2,lon2):
    R=6371.0;p1=math.radians(lat1);p2=math.radians(lat2);dp=math.radians(lat2-lat1);dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def nearby(lat,lon):
    key=(round(lat,3),round(lon,3))
    if key in CACHE and time.time()-CACHE[key][0]<300:return CACHE[key][1]
    q=f'''[out:json][timeout:20];(nwr["amenity"="restaurant"](around:{RADIUS},{lat},{lon});nwr["amenity"="fast_food"](around:{RADIUS},{lat},{lon});nwr["amenity"="cafe"](around:{RADIUS},{lat},{lon}););out center 100;'''
    last=None
    for ep in ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]:
        try:
            r=requests.post(ep,data={"data":q},headers={"User-Agent":"FoodAI-Student-Project/1.0"},timeout=25);r.raise_for_status();out=[]
            for x in r.json().get("elements",[]):
                t=x.get("tags",{});name=t.get("name")
                if not name:continue
                la=x.get("lat");lo=x.get("lon")
                if la is None or lo is None:
                    c=x.get("center",{});la=c.get("lat");lo=c.get("lon")
                if la is None or lo is None:continue
                addr=", ".join(str(v) for v in [t.get("addr:housenumber"),t.get("addr:street"),t.get("addr:suburb"),t.get("addr:city")] if v)
                out.append({"name":name,"lat":float(la),"lon":float(lo),"distance_km":round(hav(lat,lon,float(la),float(lo)),2),"cuisine":t.get("cuisine","Food & dining").replace(";",", ").replace("_"," "),"address":addr or "Open in navigation for address"})
            out.sort(key=lambda x:x["distance_km"]);clean=[];seen=set()
            for x in out:
                k=(x["name"].lower(),round(x["lat"],4),round(x["lon"],4))
                if k in seen:continue
                seen.add(k);clean.append(x)
                if len(clean)>=18:break
            CACHE[key]=(time.time(),clean);return clean
        except Exception as e:last=e
    raise RuntimeError(f"Restaurant service unavailable: {last}")

@app.get("/")
def home(): return Response(HTML,mimetype="text/html")

@app.get("/api/health")
def health():
    ok=False;installed=False
    try:
        r=requests.get(f"{OLLAMA_URL}/api/tags",timeout=3);r.raise_for_status();ok=True
        installed=any(m.get("name","").startswith(OLLAMA_MODEL) for m in r.json().get("models",[]))
    except: pass
    return jsonify(ok=True,ollama=ok,model_installed=installed,model=OLLAMA_MODEL,telegram_configured=bool(TG_TOKEN and TG_CHAT))

@app.post("/api/recognize")
def api_recognize():
    start=time.time()
    try:
        p=request.get_json(force=True);data=p.get("image","")
        if not data:return jsonify(ok=False,error="No camera image received."),400
        b64,_=prepare_image(data);r=recognize(b64);r["ok"]=True;r["latency_seconds"]=round(time.time()-start,2);return jsonify(r)
    except requests.ConnectionError:return jsonify(ok=False,error="Ollama is not reachable. Keep the Ollama app open."),503
    except Exception as e:
        print("recognition error:",e);return jsonify(ok=False,error=str(e)),500

@app.post("/api/restaurants")
def api_restaurants():
    try:
        p=request.get_json(force=True);lat=float(p["lat"]);lon=float(p["lon"]);return jsonify(ok=True,restaurants=nearby(lat,lon),radius_meters=RADIUS)
    except Exception as e:return jsonify(ok=False,restaurants=[],error=str(e)),500

@app.post("/api/notify")
def notify():
    try:
        if not (TG_TOKEN and TG_CHAT):return jsonify(ok=True,sent=False,configured=False)
        p=request.get_json(force=True);_,jpg=prepare_image(p.get("image",""));r=p.get("recognition",{});n=r.get("nutrition",{})
        text=f'''🍽 FOODAI SCAN

Food: {r.get("food_name","Unknown")}
Confidence: {r.get("confidence",0)}%
Cuisine: {r.get("cuisine","Unknown")}

Estimated nutrition:
Calories: {n.get("calories","—")} kcal
Protein: {n.get("protein_g","—")} g
Carbs: {n.get("carbs_g","—")} g
Fat: {n.get("fat_g","—")} g
Fiber: {n.get("fiber_g","—")} g

Time: {datetime.now().strftime("%d %b %Y, %I:%M %p")}'''
        lat,lon=p.get("lat"),p.get("lon")
        if lat is not None and lon is not None:text+=f"\n\n📍 https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
        rr=requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",data={"chat_id":TG_CHAT,"caption":text},files={"photo":("foodai.jpg",jpg,"image/jpeg")},timeout=20);rr.raise_for_status()
        return jsonify(ok=True,sent=True,configured=True)
    except Exception as e:return jsonify(ok=False,sent=False,error=str(e)),500

if __name__=="__main__":
    print("\n"+"="*64)
    print(" FOODAI — RECOGNITION + NUTRITION + NEARBY RESTAURANTS")
    print("="*64)
    print(" Local URL: http://127.0.0.1:8000")
    print(" Model:",OLLAMA_MODEL)
    print(" Telegram:","CONFIGURED" if TG_TOKEN and TG_CHAT else "NOT CONFIGURED YET")
    print("="*64+"\n")
    app.run(host="0.0.0.0",port=8000,debug=False,threaded=True)
