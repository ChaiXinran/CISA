"""Offline Three.js globe page generation for the PyQt WebEngine view."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from .globe_view import load_political_texture


def default_three_runtime_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "web" / "three.min.js"


def _write_texture(path: Path) -> None:
    indices, colorscale = load_political_texture(width=1441, height=721)
    palette = []
    for _, color in colorscale:
        red, green, blue = map(int, re.findall(r"\d+", str(color))[:3])
        palette.append((red, green, blue))
    pixels = np.zeros((*indices.shape, 3), dtype=np.uint8)
    for index, color in enumerate(palette):
        pixels[indices.astype(np.uint8) == index] = color
    Image.fromarray(np.flipud(pixels), mode="RGB").save(path, optimize=True)


def _vendor_payload(mapped: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for row in mapped.itertuples(index=False):
        rows.append({
            "vendor": str(row.vendor_clean),
            "country": str(row.country),
            "city": str(row.city),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "count": int(row.count),
            "knownShare": float(row.known_share),
        })
    return rows


def write_three_globe_page(
    mapped: pd.DataFrame,
    directory: str | Path,
    filename: str = "globe.html",
) -> Path:
    """Write one fully local Three.js globe page for the current filtered rows."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    runtime_source = default_three_runtime_path()
    if not runtime_source.exists():
        raise FileNotFoundError(f"缺少 Three.js 离线运行文件：{runtime_source}")
    runtime_target = target / "three.min.js"
    if not runtime_target.exists() or runtime_target.stat().st_size != runtime_source.stat().st_size:
        shutil.copyfile(runtime_source, runtime_target)
    texture_path = target / "earth-political.png"
    if not texture_path.exists():
        _write_texture(texture_path)

    payload = json.dumps(_vendor_payload(mapped), ensure_ascii=False).replace("</", "<\\/")
    page = target / filename
    page.write_text(_page_html(payload), encoding="utf-8")
    return page


def _page_html(payload: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{width:100%;height:100%;margin:0;overflow:hidden;background:#020813;color:#edf8ff;
font-family:'Microsoft YaHei','Segoe UI',sans-serif}}
#stage{{position:absolute;inset:0}} canvas{{display:block}}
#title{{position:absolute;z-index:5;left:18px;top:12px;font-size:17px;font-weight:700;pointer-events:none}}
#hint{{font-size:12px;color:#8aa6b8;font-weight:400;margin-left:8px}}
#legend{{position:absolute;z-index:5;right:16px;bottom:18px;width:132px;padding:9px 11px;border-radius:9px;
background:rgba(5,19,32,.88);border:1px solid rgba(174,216,231,.35);font-size:11px;color:#d9edf7}}
#gradient{{height:7px;margin:7px 0 3px;border-radius:5px;background:linear-gradient(90deg,#ffe77a,#f59e42,#ce382f)}}
#labels{{position:absolute;inset:0;z-index:4;pointer-events:none}}
.vendor-label{{position:absolute;display:none;transform:translate(-50%,-115%);padding:4px 8px;border-radius:8px;
border:1px solid rgba(218,241,255,.86);background:rgba(5,18,31,.94);color:#fff;font-size:13px;font-weight:650;
white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.52);pointer-events:auto;cursor:pointer;will-change:transform,left,top}}
.vendor-label:hover{{background:#17445d;border-color:#fff}}
#tooltip{{position:absolute;z-index:9000;display:none;pointer-events:none;min-width:150px;padding:9px 11px;border-radius:9px;
background:rgba(4,17,29,.97);border:1px solid rgba(210,238,250,.8);color:#effaff;font-size:12px;line-height:1.55;
white-space:pre-line;box-shadow:0 5px 18px rgba(0,0,0,.56);transform:translate(12px,12px)}}
</style></head><body>
<div id="stage"></div><div id="labels"></div><div id="tooltip"></div>
<div id="title">KEV 厂商总部位置<span id="hint">拖拽旋转 · 滚轮缩放 · 点击厂商筛选</span></div>
<div id="legend">点大小：KEV 记录数<div id="gradient"></div><div>颜色：Known 占比 0% → 100%</div></div>
<script id="vendor-data" type="application/json">{payload}</script>
<script src="three.min.js"></script><script>
const vendors = JSON.parse(document.getElementById('vendor-data').textContent);
const stage = document.getElementById('stage');
const labelLayer = document.getElementById('labels');
const tooltip = document.getElementById('tooltip');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x020813);
const camera = new THREE.PerspectiveCamera(39, 1, 0.05, 80);
const renderer = new THREE.WebGLRenderer({{antialias:true,powerPreference:'high-performance'}});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
renderer.outputEncoding = THREE.sRGBEncoding;
stage.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0x9ec8d8, 1.15));
const sunlight = new THREE.DirectionalLight(0xffffff, 2.25);
sunlight.position.set(4, 2.5, 5); scene.add(sunlight);
const texture = new THREE.TextureLoader().load('./earth-political.png', render);
texture.encoding = THREE.sRGBEncoding;
texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
const earth = new THREE.Mesh(
  new THREE.SphereGeometry(1, 96, 64),
  new THREE.MeshPhongMaterial({{map:texture,shininess:3,specular:0x17394a}})
);
scene.add(earth);

const atmosphere = new THREE.Mesh(
  new THREE.SphereGeometry(1.035, 72, 48),
  new THREE.ShaderMaterial({{
    transparent:true,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false,
    vertexShader:`varying vec3 n;varying vec3 p;void main(){{n=normalize(normalMatrix*normal);p=(modelViewMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*vec4(p,1.);}}`,
    fragmentShader:`varying vec3 n;varying vec3 p;void main(){{float i=pow(0.72-dot(n,normalize(-p)),2.6);gl_FragColor=vec4(.18,.62,.86,i*.42);}}`
  }})
); scene.add(atmosphere);

let seed=812739; function random(){{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}}
const starPositions=[]; const starColors=[];
for(let i=0;i<1800;i++){{
  const z=random()*2-1,a=random()*Math.PI*2,r=Math.sqrt(1-z*z),radius=18+random()*10;
  starPositions.push(radius*r*Math.cos(a),radius*z,radius*r*Math.sin(a));
  const b=.80+random()*.20; starColors.push(.84*b,.92*b,b);
}}
const starGeometry=new THREE.BufferGeometry();
starGeometry.setAttribute('position',new THREE.Float32BufferAttribute(starPositions,3));
starGeometry.setAttribute('color',new THREE.Float32BufferAttribute(starColors,3));
scene.add(new THREE.Points(starGeometry,new THREE.PointsMaterial({{size:.11,vertexColors:true,sizeAttenuation:true,transparent:true,opacity:1,depthWrite:false}})));

const markerGroup=new THREE.Group(); scene.add(markerGroup);
const maxLog=Math.max(1,...vendors.map(v=>Math.log1p(v.count)));
const markerGeometry=new THREE.SphereGeometry(1,20,14);
const rayTargets=[]; const labels=[];
function positionFor(v,radius){{
  const lat=THREE.MathUtils.degToRad(v.latitude),lon=THREE.MathUtils.degToRad(v.longitude);
  return new THREE.Vector3(Math.cos(lat)*Math.cos(lon)*radius,Math.sin(lat)*radius,-Math.cos(lat)*Math.sin(lon)*radius);
}}
vendors.forEach((v,index)=>{{
  const t=Math.max(0,Math.min(1,v.knownShare));
  const color=new THREE.Color().lerpColors(new THREE.Color(0xffe77a),new THREE.Color(0xce382f),t);
  const marker=new THREE.Mesh(markerGeometry,new THREE.MeshPhongMaterial({{color,emissive:color,emissiveIntensity:.25,shininess:18}}));
  marker.scale.setScalar(.018+.037*Math.log1p(v.count)/maxLog);
  marker.position.copy(positionFor(v,1.025)); marker.userData={{vendor:v.vendor,index}};
  markerGroup.add(marker); rayTargets.push(marker);
  const label=document.createElement('button'); label.className='vendor-label';
  label.textContent=v.vendor+' · '+v.count; label.onclick=()=>selectVendor(v.vendor);
  label.addEventListener('pointerenter',e=>showTooltip(v,e.clientX,e.clientY));
  label.addEventListener('pointermove',e=>moveTooltip(e.clientX,e.clientY));
  label.addEventListener('pointerleave',hideTooltip);
  labelLayer.appendChild(label); labels.push(label);
}});
function selectVendor(vendor){{window.location.hash='vendor='+encodeURIComponent(vendor);}}
function tooltipText(v){{return v.vendor+'\\n'+v.city+', '+v.country+'\\n当前 KEV 记录：'+v.count+'\\nKnown 占比：'+(v.knownShare*100).toFixed(1)+'%';}}
function moveTooltip(x,y){{tooltip.style.left=x+'px';tooltip.style.top=y+'px';}}
function showTooltip(v,x,y){{tooltip.textContent=tooltipText(v);tooltip.style.display='block';moveTooltip(x,y);}}
function hideTooltip(){{tooltip.style.display='none';}}

let theta=.80,phi=1.16,distance=3.65,dragging=false,lastX=0,lastY=0,downX=0,downY=0,moved=false,framePending=false;
function updateCamera(){{
  camera.position.set(distance*Math.sin(phi)*Math.cos(theta),distance*Math.cos(phi),distance*Math.sin(phi)*Math.sin(theta));
  camera.lookAt(0,0,0);
}}
function schedule(){{if(framePending)return;framePending=true;requestAnimationFrame(()=>{{framePending=false;render();}})}}
function render(){{
  updateCamera(); renderer.render(scene,camera);
  const cameraDirection=camera.position.clone().normalize();
  labels.forEach((label,index)=>{{
    const marker=rayTargets[index],normal=marker.position.clone().normalize();
    const facing=normal.dot(cameraDirection);
    if(facing<.08){{label.style.display='none';return;}}
    const point=marker.position.clone().project(camera);
    if(Math.abs(point.x)>1.05||Math.abs(point.y)>1.05){{label.style.display='none';return;}}
    const x=(point.x*.5+.5)*renderer.domElement.clientWidth;
    const y=(-point.y*.5+.5)*renderer.domElement.clientHeight;
    const radial=Math.hypot(point.x,point.y);
    label.style.display='block';label.style.left=x+'px';label.style.top=(y-5)+'px';
    label.style.zIndex=String(5000-Math.round(radial*1000));
    label.style.opacity=String(Math.min(1,.56+facing*.55));
  }});
}}
function resize(){{
  const width=stage.clientWidth,height=stage.clientHeight;
  renderer.setSize(width,height,true);camera.aspect=width/Math.max(1,height);camera.updateProjectionMatrix();schedule();
}}
const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2();
function markerAt(e){{
  const rect=renderer.domElement.getBoundingClientRect();mouse.x=(e.clientX-rect.left)/rect.width*2-1;mouse.y=-(e.clientY-rect.top)/rect.height*2+1;
  raycaster.setFromCamera(mouse,camera);return raycaster.intersectObjects(rayTargets,false)[0];
}}
renderer.domElement.addEventListener('pointerdown',e=>{{dragging=true;moved=false;downX=lastX=e.clientX;downY=lastY=e.clientY;hideTooltip();renderer.domElement.setPointerCapture(e.pointerId);}});
renderer.domElement.addEventListener('pointermove',e=>{{
  if(dragging){{
    if(Math.hypot(e.clientX-downX,e.clientY-downY)>3)moved=true;
    theta+=(e.clientX-lastX)*.006;phi=Math.max(.10,Math.min(Math.PI-.10,phi-(e.clientY-lastY)*.006));lastX=e.clientX;lastY=e.clientY;schedule();return;
  }}
  const hit=markerAt(e);if(hit)showTooltip(vendors[hit.object.userData.index],e.clientX,e.clientY);else hideTooltip();
}});
renderer.domElement.addEventListener('pointerleave',()=>{{if(!dragging)hideTooltip();}});
renderer.domElement.addEventListener('pointerup',e=>{{dragging=false;renderer.domElement.releasePointerCapture(e.pointerId);}});
renderer.domElement.addEventListener('wheel',e=>{{e.preventDefault();distance=Math.max(1.82,Math.min(4.6,distance*Math.exp(e.deltaY*.001)));hideTooltip();schedule();}},{{passive:false}});
renderer.domElement.addEventListener('click',e=>{{
  if(moved)return;const hit=markerAt(e);if(hit)selectVendor(hit.object.userData.vendor);
}});
window.addEventListener('resize',resize);resize();
</script></body></html>"""
