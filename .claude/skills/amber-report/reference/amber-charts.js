/* ============================================================================
   AMBER LEDGER — optional canvas charts. Inline this in a <script> block AFTER
   the report body. CSP-safe: no libraries, no remote anything. Colors are read
   from the CSS custom properties so the charts can never drift from the palette.

   The ledger/table/stat-grid are pure CSS and need none of this. Reach for a
   chart only for a genuine trend or distribution (rating over time, win% by
   phase, a stars-vs-fit scatter). Every chart is enhancement — the report must
   read fully with JS stripped.

   API:
     AmberChart.line("cv", [{x,y}...], {yMin,yMax,xLabel,yLabel,threshold})
     AmberChart.bars("cv", [{label,value,flag}...], {yMax,unit})
     AmberChart.scatter("cv", [{x,y,label,flag}...], {xLog,yMin,yMax,xLabel,yLabel,threshold})
   Call once after DOMContentLoaded; each fn self-installs a ResizeObserver.
   ============================================================================ */
var AmberChart=(function(){
  var css=getComputedStyle(document.documentElement);
  function c(n,f){return (css.getPropertyValue(n)||"").trim()||f;}
  var AMBER=c("--amber","#A65A00"),OLIVE=c("--olive","#5B614E"),INK=c("--carbon","#15180F"),
      GRID="rgba(91,97,78,0.22)",THR="rgba(166,90,0,0.55)",MONO=c("--mono","monospace");

  function fit(cv){var w=cv.clientWidth||600,h=cv.clientHeight||300,d=Math.min(window.devicePixelRatio||1,2);
    cv.width=w*d;cv.height=h*d;var x=cv.getContext("2d");x.setTransform(d,0,0,d,0,0);x.clearRect(0,0,w,h);return {x:x,w:w,h:h};}
  function mount(cv,render){if(!cv||!cv.getContext)return;render();
    if(window.ResizeObserver){new ResizeObserver(render).observe(cv);}else{window.addEventListener("resize",render);}}
  function el(id){return typeof id==="string"?document.getElementById(id):id;}

  function line(id,pts,o){o=o||{};var cv=el(id);mount(cv,function(){
    var g=fit(cv),x=g.x,W=g.w,H=g.h,mL=44,mR=14,mT=14,mB=28,pw=W-mL-mR,ph=H-mT-mB;
    var yMin=o.yMin!=null?o.yMin:Math.min.apply(0,pts.map(function(p){return p.y;}));
    var yMax=o.yMax!=null?o.yMax:Math.max.apply(0,pts.map(function(p){return p.y;}));
    var xs=pts.map(function(p){return p.x;}),xMin=Math.min.apply(0,xs),xMax=Math.max.apply(0,xs);
    function X(v){return mL+(xMax===xMin?0:(v-xMin)/(xMax-xMin))*pw;}
    function Y(v){return mT+(1-(v-yMin)/(yMax-yMin||1))*ph;}
    x.font="10px "+MONO;x.textBaseline="middle";
    for(var i=0;i<=4;i++){var yv=yMin+(yMax-yMin)*i/4,yy=Y(yv);
      x.strokeStyle=GRID;x.beginPath();x.moveTo(mL,yy+.5);x.lineTo(mL+pw,yy+.5);x.stroke();
      x.fillStyle=OLIVE;x.textAlign="right";x.fillText(Math.round(yv),mL-8,yy);}
    if(o.threshold!=null){var ty=Y(o.threshold);x.strokeStyle=THR;x.setLineDash([4,3]);
      x.beginPath();x.moveTo(mL,ty+.5);x.lineTo(mL+pw,ty+.5);x.stroke();x.setLineDash([]);}
    x.strokeStyle=AMBER;x.lineWidth=2;x.beginPath();
    pts.forEach(function(p,i){var px=X(p.x),py=Y(p.y);i?x.lineTo(px,py):x.moveTo(px,py);});x.stroke();
    x.fillStyle=AMBER;var last=pts[pts.length-1];x.beginPath();x.arc(X(last.x),Y(last.y),3.5,0,7);x.fill();
    if(o.yLabel){x.save();x.translate(11,mT+ph/2);x.rotate(-Math.PI/2);x.textAlign="center";x.fillStyle=OLIVE;x.fillText(o.yLabel,0,0);x.restore();}
  });}

  function bars(id,data,o){o=o||{};var cv=el(id);mount(cv,function(){
    var g=fit(cv),x=g.x,W=g.w,H=g.h,mL=40,mR=14,mT=12,mB=34,pw=W-mL-mR,ph=H-mT-mB;
    var yMax=o.yMax!=null?o.yMax:Math.max.apply(0,data.map(function(d){return d.value;}));
    var bw=pw/data.length*0.62,gap=pw/data.length;
    x.font="10px "+MONO;
    for(var i=0;i<=4;i++){var yv=yMax*i/4,yy=mT+(1-i/4)*ph;
      x.strokeStyle=GRID;x.beginPath();x.moveTo(mL,yy+.5);x.lineTo(mL+pw,yy+.5);x.stroke();
      x.fillStyle=OLIVE;x.textBaseline="middle";x.textAlign="right";x.fillText(Math.round(yv)+(o.unit||""),mL-6,yy);}
    data.forEach(function(d,i){var bx=mL+gap*i+(gap-bw)/2,bh=(d.value/(yMax||1))*ph,by=mT+ph-bh;
      x.fillStyle=d.flag?AMBER:OLIVE;x.fillRect(bx,by,bw,bh);
      x.fillStyle=OLIVE;x.textAlign="center";x.textBaseline="top";x.fillText(d.label,bx+bw/2,mT+ph+7);});
  });}

  function scatter(id,pts,o){o=o||{};var cv=el(id);mount(cv,function(){
    var g=fit(cv),x=g.x,W=g.w,H=g.h,mL=44,mR=16,mT=14,mB=30,pw=W-mL-mR,ph=H-mT-mB;
    var yMin=o.yMin!=null?o.yMin:0,yMax=o.yMax!=null?o.yMax:10;
    var xv=pts.map(function(p){return o.xLog?Math.log10(p.x):p.x;}),xMin=Math.min.apply(0,xv),xMax=Math.max.apply(0,xv);
    function X(v){var t=o.xLog?Math.log10(v):v;return mL+(t-xMin)/(xMax-xMin||1)*pw;}
    function Y(v){return mT+(1-(v-yMin)/(yMax-yMin||1))*ph;}
    x.font="10px "+MONO;x.textBaseline="middle";
    [yMin,(yMin+yMax)/2,yMax].concat(o.threshold!=null?[o.threshold]:[]).forEach(function(v){
      var yy=Y(v),t=o.threshold!=null&&v===o.threshold;x.strokeStyle=t?THR:GRID;x.setLineDash(t?[4,3]:[]);
      x.beginPath();x.moveTo(mL,yy+.5);x.lineTo(mL+pw,yy+.5);x.stroke();x.setLineDash([]);
      x.fillStyle=t?"#8A4A00":OLIVE;x.textAlign="right";x.fillText(t?v+" ▸":Math.round(v),mL-8,yy);});
    pts.forEach(function(p){var px=X(p.x),py=Y(p.y);x.beginPath();x.arc(px,py,p.flag?6.5:5,0,7);
      x.fillStyle=p.flag?AMBER:OLIVE;x.globalAlpha=p.flag?1:.82;x.fill();x.globalAlpha=1;
      if(p.flag&&p.label){x.fillStyle=INK;x.textAlign=px>mL+pw-120?"right":"left";
        x.fillText(p.label,px>mL+pw-120?px-10:px+10,py-1+(p.dy||0));}});
    if(o.yLabel){x.save();x.translate(12,mT+ph/2);x.rotate(-Math.PI/2);x.textAlign="center";x.fillStyle=OLIVE;x.fillText(o.yLabel,0,0);x.restore();}
  });}

  return {line:line,bars:bars,scatter:scatter};
})();
