const canvas=document.getElementById('face'),ctx=canvas.getContext('2d');
let state='idle', energy=0, bands={bass:0,mid:0,high:0};
const points=[];const rings=[32,44,54,48,32];
for(let row=0;row<rings.length;row++)for(let col=0;col<rings[row];col++){
  const angle=2*Math.PI*col/rings[row],v=(row+1)/(rings.length+1),radius=.17+v*.36;
  points.push({x:Math.cos(angle)*radius,y:Math.sin(angle)*radius*.88,row,col,angle,phase:Math.random()*6.28});
}
// Facial landmarks live in the same mesh and change with voice amplitude.
for(const [x,y] of [[-.19,-.1],[-.12,-.105],[.12,-.105],[.19,-.1],[-.13,.17],[-.06,.195],[0,.202],[.06,.195],[.13,.17],[0,.02]])
  points.push({x,y,row:6,col:0,angle:0,phase:Math.random()*6});
let width=0,height=0,dpr=1;
function resize(){dpr=Math.min(devicePixelRatio||1,2);width=canvas.clientWidth;height=canvas.clientHeight;canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0)}
new ResizeObserver(resize).observe(canvas);resize();
export function setState(value){state=value;document.getElementById('state').textContent=value.toUpperCase()}
export function setBands(value){bands=value;energy=Math.max(value.bass,value.mid,value.high)}
function frame(t){t*=.001;ctx.clearRect(0,0,width,height);const size=Math.min(width,height)*.91,cx=width/2,cy=height/2;
 const active=state==='listening'?1:state==='speaking'?.85:state==='thinking'?.6:.18;
 const position=points.map(p=>{const pulse=Math.sin(t*1.8+p.phase)*(.005+active*.008)+energy*.023;
  const twist=Math.sin(t*.35+p.y*4)*.015;
  return {x:cx+(p.x*(1+pulse)+twist)*size,y:cy+(p.y*(1+pulse))*size}});
 ctx.lineWidth=.7;
 for(let i=0;i<points.length;i++){
  let links=0;for(let j=i+1;j<points.length && links<7;j++){
   const dx=position[i].x-position[j].x,dy=position[i].y-position[j].y,d=Math.hypot(dx,dy);
   if(d<size*.09){const a=(1-d/(size*.09))*(.13+active*.22+energy*.25);
    ctx.strokeStyle=`rgba(${state==='error'?255:72},${state==='error'?100:210},${state==='error'?110:224},${a})`;
    ctx.beginPath();ctx.moveTo(position[i].x,position[i].y);ctx.lineTo(position[j].x,position[j].y);ctx.stroke();links++}
  }
 }
 for(let i=0;i<points.length;i++){const p=position[i],brightness=.42+Math.sin(t*2+points[i].phase)*.16+energy*.35;
  ctx.fillStyle=state==='error'?`rgba(255,115,131,${brightness})`:`rgba(${90+Math.floor(bands.high*85)},${210+Math.floor(bands.mid*30)},239,${brightness})`;
  ctx.beginPath();ctx.arc(p.x,p.y,points[i].row===6?2.2:1.2+energy*1.8,0,Math.PI*2);ctx.fill()}
 requestAnimationFrame(frame)}requestAnimationFrame(frame);
