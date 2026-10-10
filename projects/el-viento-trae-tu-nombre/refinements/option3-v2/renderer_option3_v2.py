import cv2, numpy as np, math, wave, hashlib, json, subprocess
from pathlib import Path

ROOT = Path('/mnt/data')
OUT = ROOT / 'el_viento_option3_v2'
OUT.mkdir(exist_ok=True)
AUDIO = ROOT / 'El Viento trae tu nombre (Remastered).wav'
FPS = 24
W, H = 1280, 720
TOTAL_FRAMES = 2704
DURATION = 112.68

hero = {
    1:'weathered_canvas_nautical_map.png',
    2:'antique_embroidered_fantasy_map.png',
    3:'antique_map_dissolving_into_ocean.png',
    4:'impasto_island_village_map.png',
    5:'fortress_on_the_coastal_map.png',
    6:'dreamlike_fortress_coastline_on_linen.png',
    7:'fog_shrouded_fantasy_map.png',
    8:'ghostly_travelers_on_an_ancient_cloth_map.png',
    9:'ancient_embroidered_map_of_journeys.png',
    10:'glowing_map_inspired_tapestry_thread.png',
    11:'glowing_thread_through_the_void.png'
}
fx1 = {
    1:'weathered_nautical_map_on_linen.png',
    2:'embroidered_fantasy_map_and_compass_rose.png',
    3:'embroidered_stormsea_map.png',
    4:'stormy_impasto_island_village.png',
    5:'medieval_coastal_fortress_map.png',
    6:'golden_hour_castle_over_misty_bay.png',
    7:'atmospheric_fantasy_map_in_mist.png',
    8:'ghostly_figures_in_an_ink_wash_landscape.png',
    9:'weathered_embroidered_fantasy_map_tapestry.png',
    10:'glowing_twisted_fiber_rope.png'
}
fx2 = {i: ROOT / 'fx_motion_variants_02' / f'shot_{i:02d}_fx_motion_variant_b2.png' for i in range(2,12)}
spans=[(1,0,257),(2,258,515),(3,516,773),(4,774,1031),(5,1032,1289),(6,1290,1547),(7,1548,1805),(8,1806,2063),(9,2064,2321),(10,2322,2547),(11,2548,2703)]
mode={1:'living',2:'living',3:'living',4:'living',5:'cinematic',6:'living',7:'living',8:'living',9:'cinematic',10:'living',11:'cinematic'}

def sha256_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fit(path):
    im = cv2.imread(str(path), cv2.IMREAD_COLOR)
    ih, iw = im.shape[:2]
    target = W / H
    src = iw / ih
    if src > target:
        cw = int(ih * target); x = (iw - cw) // 2; im = im[:, x:x+cw]
    else:
        ch = int(iw / target); y = (ih - ch) // 2; im = im[y:y+ch, :]
    return cv2.resize(im, (W,H), interpolation=cv2.INTER_AREA if im.shape[1] > W else cv2.INTER_LANCZOS4)

def sstep(x):
    x=np.clip(x,0,1); return x*x*(3-2*x)

def lerp(a,b,t):
    return cv2.addWeighted(a,1.0-t,b,t,0)

imgs={i:fit(ROOT/p) for i,p in hero.items()}
vars1={i:fit(ROOT/p) for i,p in fx1.items()}
vars2={i:fit(p) for i,p in fx2.items() if p.exists()}

with wave.open(str(AUDIO),'rb') as wf:
    sr=wf.getframerate(); n=wf.getnframes(); ch=wf.getnchannels(); raw=wf.readframes(n)
a=np.frombuffer(raw,dtype='<i2').reshape(-1,ch).astype(np.float32).mean(axis=1)/32768.0
energy=[]
for fi in range(TOTAL_FRAMES):
    i0=int((fi/FPS)*sr); i1=min(len(a),int(((fi+1)/FPS)*sr)); seg=a[i0:i1]
    energy.append(float(np.sqrt(np.mean(seg*seg)+1e-12)) if len(seg) else 0.0)
energy=np.array(energy); lo,hi=np.percentile(energy,[10,95]); energy=np.clip((energy-lo)/(hi-lo+1e-6),0,1)

Y,X=np.mgrid[0:H,0:W].astype(np.float32); rng=np.random.default_rng(1302)
edge=np.minimum.reduce([X/(W*.12+1),(W-1-X)/(W*.12+1),Y/(H*.12+1),(H-1-Y)/(H*.12+1)])
edge=np.clip(edge,0,1).astype(np.float32)
noise_small=cv2.resize(rng.normal(0,1,(H//24,W//24)).astype(np.float32),(W,H),interpolation=cv2.INTER_CUBIC)
noise_small=cv2.GaussianBlur(noise_small,(0,0),5)
canvas_tex=cv2.normalize(noise_small,None,0,1,cv2.NORM_MINMAX)
thread_field=cv2.GaussianBlur(cv2.resize(rng.random((H//20,W//20),dtype=np.float32),(W,H),interpolation=cv2.INTER_CUBIC),(0,0),4)

def gray_edges(im,blur=1.5,low=50,high=140):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY); g=cv2.GaussianBlur(g,(0,0),blur)
    e=cv2.Canny(g,low,high); e=cv2.GaussianBlur(e,(0,0),1.2)
    return e.astype(np.float32)/255.0

def colorize_mask(mask,color,alpha=1.0):
    out=np.zeros((H,W,3),np.float32)
    out[...,0]=color[0]; out[...,1]=color[1]; out[...,2]=color[2]
    return out*(mask[...,None]*alpha)

def add_canvas_weave(im,strength=0.1):
    weave=(0.65*np.sin(X/3.2)+0.45*np.sin(Y/3.1)+0.2*np.sin((X+Y)/5.2))
    weave=cv2.GaussianBlur(weave,(0,0),0.8)
    f=im.astype(np.float32)
    f=f*(1.0-strength)+np.clip(f+weave[...,None]*15*strength,0,255)*strength
    return np.clip(f,0,255).astype(np.uint8)

def flow_remap(im,phase,amp=1.0,orient='both'):
    dx=np.zeros((H,W),np.float32); dy=np.zeros((H,W),np.float32)
    if orient in ('both','x'): dx+=amp*(0.8*np.sin(Y/51+phase)+0.25*np.sin((X+Y)/129-phase*0.7))*edge
    if orient in ('both','y'): dy+=amp*(0.7*np.sin(X/68-phase*0.4)+0.3*np.cos((X-Y)/151+phase))*edge
    return cv2.remap(im,X+dx,Y+dy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def mist_layer(phase,speed=1.0):
    field=cv2.GaussianBlur(cv2.resize(rng.random((H//28,W//28),dtype=np.float32),(W,H),interpolation=cv2.INTER_CUBIC),(0,0),7)
    return cv2.warpAffine(field,np.float32([[1,0,18*np.sin(phase*speed)],[0,1,-14*np.cos(phase*speed)]]),(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)

def apply_mist(im,phase,amount=0.08,cool=True):
    f=im.astype(np.float32); m=mist_layer(phase); alpha=np.clip((m-0.45)*amount*3,0,amount)
    tint=np.zeros_like(f); tint[:]=(112,116,122) if cool else (130,125,118)
    return np.clip(f*(1-alpha[...,None])+tint*alpha[...,None],0,255).astype(np.uint8)

def add_embroidery(im,phase,intensity=0.35):
    edges=gray_edges(vars1.get(2,imgs[2]),blur=1.2,low=70,high=160)
    routes=cv2.GaussianBlur(edges,(0,0),1.4)
    shimmer=(0.65+0.35*np.sin(phase*2+X/40))*routes
    overlay=np.zeros((H,W,3),np.float32)
    overlay+=colorize_mask(shimmer,(40,140,210),0.7)
    overlay+=colorize_mask(shimmer*0.85,(220,180,50),0.55)
    overlay+=colorize_mask(shimmer*0.65,(30,70,180),0.35)
    return np.clip(im.astype(np.float32)+overlay*intensity,0,255).astype(np.uint8)

def add_map_ink(im,phase,intensity=0.3):
    edges=gray_edges(vars1.get(1,imgs[1]),blur=1.1,low=60,high=150)
    reveal=np.clip((phase*1.25)-canvas_tex*0.55,0,1)
    overlay=colorize_mask(edges*reveal,(35,55,75),1.0)
    return np.clip(im.astype(np.float32)+overlay*intensity,0,255).astype(np.uint8)

def add_currents(im,phase,intensity=0.22):
    wave=0.5+0.5*np.sin((X/18+phase*5)+0.35*np.sin(Y/41-phase))
    wave*=np.clip((Y/H)*1.3,0.15,1.0)
    blue=colorize_mask(wave.astype(np.float32),(190,120,40),0.22)
    teal=colorize_mask(np.roll(wave,15,axis=1).astype(np.float32),(120,145,35),0.16)
    return np.clip(im.astype(np.float32)+(blue+teal)*intensity,0,255).astype(np.uint8)

def add_silhouettes(im,phase,intensity=0.9):
    g=cv2.cvtColor(vars1.get(8,imgs[8]),cv2.COLOR_BGR2GRAY)
    mask=(g<np.percentile(g,34)).astype(np.float32); mask=cv2.GaussianBlur(mask,(0,0),2.5)
    reveal=np.clip(0.35+0.45*np.sin(phase*2.2)+0.35*(1-canvas_tex),0,1)
    alpha=mask*reveal*intensity*0.6
    return np.clip(im.astype(np.float32)*(1-alpha[...,None]),0,255).astype(np.uint8)

def tapestry_collage(phase):
    tiles=[imgs[1],imgs[2],imgs[3],imgs[4],imgs[5],imgs[6],imgs[7],imgs[8]]
    out=np.zeros((H,W,3),np.float32)
    grid=[(0,0),(W//4,0),(W//2,0),(3*W//4,0),(0,H//2),(W//4,H//2),(W//2,H//2),(3*W//4,H//2)]
    tw,th=W//4,H//2
    for tile,(x,y) in zip(tiles,grid):
        out[y:y+th,x:x+tw]=cv2.resize(tile,(tw,th),interpolation=cv2.INTER_AREA).astype(np.float32)
    out=cv2.GaussianBlur(out,(0,0),1.2); fold=0.18*(1-abs(phase-0.5)*2)
    out*=np.clip(edge*1.2,0,1)[...,None]*(1.0-fold*0.2)
    out=add_canvas_weave(np.clip(out,0,255).astype(np.uint8),0.24)
    return add_embroidery(out,phase*math.tau,0.45)

def thread_core(phase):
    out=np.zeros((H,W,3),np.uint8); cx=W*0.5+math.sin(phase*math.tau)*W*0.08
    y=np.arange(H); xline=(cx+np.sin(y/28+phase*5.4)*18+np.sin(y/9-phase*3.1)*4).astype(np.int32)
    pts=np.stack([xline,y],axis=1).reshape(-1,1,2)
    for radius,color in [(11,(70,120,255)),(8,(80,180,255)),(5,(120,220,255)),(2,(220,240,255))]:
        cv2.polylines(out,[pts],False,color,radius,lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(out,(0,0),1.2)

def base_morph(i,ph):
    a=imgs[i].astype(np.float32); b=vars1.get(i,imgs[i]).astype(np.float32); c=vars2.get(i,vars1.get(i,imgs[i])).astype(np.float32)
    if i==9: return tapestry_collage(ph).astype(np.uint8)
    if i==10:
        base=lerp(a.astype(np.uint8),b.astype(np.uint8),sstep(min(ph*1.2,1))*0.75)
        return np.clip(base.astype(np.float32)*0.22+thread_core(ph).astype(np.float32)*0.92,0,255).astype(np.uint8)
    if i==11: return lerp(thread_core(ph),np.zeros_like(imgs[i]),sstep(ph)*0.88)
    if ph<0.5: return lerp(a.astype(np.uint8),b.astype(np.uint8),sstep(ph/0.5)*0.62)
    return lerp(b.astype(np.uint8),c.astype(np.uint8),sstep((ph-0.5)/0.5)*0.58)

def camera_move(im,i,ph):
    z=1.0; tx=ty=rot=0.0
    if i==1:z=1.04-0.04*ph
    elif i==2:z=1.01+0.01*math.sin(ph*math.pi)
    elif i==3:tx=-9+18*ph
    elif i==4:z=1.0+0.05*ph;ty=2-4*ph
    elif i==5:tx=-8+16*ph;rot=0.38*math.sin((ph-0.5)*math.pi)
    elif i==6:ty=8-16*ph
    elif i==8:tx=-10+20*ph
    elif i==9:z=1.08-0.10*ph
    elif i==11:tx=10*math.sin(ph*math.pi);ty=-5*ph
    M=cv2.getRotationMatrix2D((W/2,H/2),rot,z);M[0,2]+=tx;M[1,2]+=ty
    return cv2.warpAffine(im,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def shot(i,ph,e):
    phase=ph*math.tau; im=base_morph(i,ph)
    if i in (1,2,3,4,6,7,8,9): im=flow_remap(im,phase,amp=(0.75 if mode[i]=='living' else 0.38)*(0.8+0.25*e))
    if i in (1,2): im=add_map_ink(im,ph,0.32 if i==1 else 0.2); im=add_embroidery(im,phase,0.22 if i==1 else 0.42)
    if i in (3,4): im=add_currents(im,ph,0.28 if i==3 else 0.18); im=add_embroidery(im,phase,0.14) if i==4 else im
    if i==5: im=add_map_ink(im,ph,0.1)
    if i in (6,7): im=apply_mist(im,phase,0.11 if i==7 else 0.07,cool=False); im=add_embroidery(im,phase,0.12 if i==6 else 0.07)
    if i==8: im=apply_mist(im,phase,0.12,cool=True); im=add_silhouettes(im,phase,1.0)
    if i==9: im=apply_mist(im,phase,0.05,cool=False)
    im=camera_move(im,i,ph); im=add_canvas_weave(im,0.08 if i<9 else 0.04)
    if i in (6,7,8): im=apply_mist(im,phase*0.8,0.06,cool=(i!=6))
    pulse=0.6*math.sin(phase*2.0)+0.4*math.sin(phase*3.7+1.2)
    mul=1.0+(0.012+0.016*e)*pulse*(1.0 if i in (2,6,9,10,11) else 0.55)
    im=np.clip(im.astype(np.float32)*mul+canvas_tex[...,None]*5.5,0,255).astype(np.uint8)
    if i==11: im=np.clip(im.astype(np.float32)*(1-sstep((ph-0.56)/0.44)),0,255).astype(np.uint8)
    return im

def pigment_transition(a,b,i,p):
    local=cv2.GaussianBlur(thread_field,(0,0),2); mask=np.clip(((0.14+0.75*p)-local)*6+0.5,0,1);mask=cv2.GaussianBlur(mask,(0,0),2.5)
    bloom=1.6*math.sin(math.pi*p);aa=cv2.GaussianBlur(a,(0,0),bloom) if bloom>0.2 else a;bb=cv2.GaussianBlur(b,(0,0),bloom) if bloom>0.2 else b
    return np.clip(aa.astype(np.float32)*(1-mask[...,None])+bb.astype(np.float32)*mask[...,None],0,255).astype(np.uint8)

owner=np.zeros(TOTAL_FRAMES,np.int16);starts={};ends={}
for i,s,e in spans:owner[s:e+1]=i;starts[i]=s;ends[i]=e
raw=OUT/'video_noaudio.mp4'
cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(raw)]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);tf=int(round(1.15*FPS))
for fi in range(TOTAL_FRAMES):
    i=int(owner[fi]);s,e=starts[i],ends[i];ph=(fi-s)/max(1,e-s);fr=shot(i,ph,float(energy[fi]))
    if i<11 and fi>e-tf:
        p=(fi-(e-tf))/tf;fr=pigment_transition(fr,shot(i+1,0,float(energy[fi])),i,p)
    proc.stdin.write(fr.tobytes())
proc.stdin.close();rc=proc.wait()
if rc:raise SystemExit(rc)
master=OUT/'El_Viento_Trae_Tu_Nombre_option3_v2_1080p.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-i',str(AUDIO),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','17','-vf','scale=1920:1080:flags=lanczos','-c:a','aac','-b:a','320k','-shortest','-movflags','+faststart',str(master)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(master)]))
meta={'master':str(master),'sha256':sha256_file(master),'audio_sha256':sha256_file(AUDIO),'frames':TOTAL_FRAMES,'fps':FPS,'probe':probe,'intent':'Option 3 reinforcement recut v2 with stronger map/embroidery/village/fort/tapestry anchors and heavier approved effect usage.'}
(OUT/'render_manifest.json').write_text(json.dumps(meta,indent=2))
