import cv2, numpy as np, wave, math, json, subprocess, time
from pathlib import Path
from scipy.signal import find_peaks

# Silver Coin V6 reference implementation.
# Adapt paths/timings per project. Keep image identity stable; use music to drive camera/light/transition energy.

OUT=Path('/mnt/data/silver_coin_v6_motion')
RW,RH,FPS=960,540,12
DW,DH=1280,720
DUR=39.3
AUDIO=Path('/mnt/data/Silver Coin  (Remastered).wav')
SCENES=[
 (0.0,10.0,Path('/mnt/data/enchanted_woodland_coin_portrait.png'),'forest_coin'),
 (10.0,20.0,Path('/mnt/data/golden_path_to_the_village.png'),'path_reveal'),
 (20.0,30.0,Path('/mnt/data/golden_haired_maiden_at_sunset.png'),'labor_end'),
 (30.0,39.3,Path('/mnt/data/twilight_inn_beneath_the_flower_crown.png'),'threshold_gold'),
]

with wave.open(str(AUDIO),'rb') as w:
    sr=w.getframerate(); raw=w.readframes(w.getnframes()); ch=w.getnchannels()
x=np.frombuffer(raw,dtype='<i2').reshape(-1,ch).mean(1).astype(np.float32)/32768
hop=1024
en=np.array([np.mean(np.abs(x[i:i+hop])) for i in range(0,len(x)-hop,hop)],np.float32)
flux=np.maximum(0,np.diff(en,prepend=en[0])); flux=np.convolve(flux,np.ones(5)/5,'same')
pk,_=find_peaks(flux,distance=max(1,int(.28*sr/hop)),prominence=np.std(flux)*.55)
pt=pk*hop/sr; pv=flux[pk]; m=pt<DUR+1; pt,pv=pt[m],pv[m]
if len(pv): pv=(pv-pv.min())/(pv.max()-pv.min()+1e-9)

def pulse(t):
    if not len(pt): return 0.0
    d=np.abs(pt-t)
    return float(np.max(np.exp(-(d/.18)**2)*(.35+.65*pv)))

def energy(t):
    i=min(len(en)-1,max(0,int(t*sr/hop)))
    v=float(np.mean(en[max(0,i-3):min(len(en),i+4)]))
    return float(np.clip((v-.025)/.15,0,1))

BASEW,BASEH=1120,630
bases=[]
for _,_,p,_ in SCENES:
    im=cv2.imread(str(p)); ih,iw=im.shape[:2]
    s=max(BASEW/iw,BASEH/ih)
    r=cv2.resize(im,(int(iw*s),int(ih*s)),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_LANCZOS4)
    y=(r.shape[0]-BASEH)//2; x0=(r.shape[1]-BASEW)//2
    bases.append(r[y:y+BASEH,x0:x0+BASEW])

Y,X=np.mgrid[0:RH,0:RW].astype(np.float32)
rad=np.sqrt(((X-RW/2)/(RW/2))**2+((Y-RH/2)/(RH/2))**2)
vign=np.clip(1-.14*np.maximum(0,rad-.48),.82,1)[...,None]
LW,LH=120,68; ly,lx=np.mgrid[0:LH,0:LW].astype(np.float32); rng=np.random.default_rng(302)
params=[(rng.uniform(.08,.92),rng.uniform(.08,.88),rng.uniform(.04,.11),rng.uniform(.08,.22),rng.uniform(0,6.28)) for _ in range(10)]

def glow_field(t):
    f=np.zeros((LH,LW),np.float32)
    for i,(px,py,sig,a,ph) in enumerate(params):
        px2=px+.02*math.sin(.16*t+ph); py2=py+.015*math.cos(.12*t+ph)
        xx=lx/LW-px2; yy=ly/LH-py2
        f += a*np.exp(-(xx*xx+yy*yy)/(2*sig*sig))
    f/=f.max()+1e-6
    return cv2.resize(f,(RW,RH),interpolation=cv2.INTER_LINEAR)

def camera(base,scale,dx,dy,angle):
    M=cv2.getRotationMatrix2D((BASEW/2,BASEH/2),angle,scale)
    M[0,2]+=dx*45; M[1,2]+=dy*28
    w=cv2.warpAffine(base,M,(BASEW,BASEH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    x=(BASEW-RW)//2; y=(BASEH-RH)//2
    return w[y:y+RH,x:x+RW]

def scene(idx,t):
    st,en_,_,kind=SCENES[idx]; u=np.clip((t-st)/(en_-st),0,1); p=pulse(t); e=energy(t)
    if kind=='forest_coin': sc=1.025+.025*u+.004*p; dx=-.55+.55*u; dy=.15*math.sin(math.pi*u); a=-.35+.55*u
    elif kind=='path_reveal': sc=1.035+.012*math.sin(math.pi*u)+.004*p; dx=-.7+1.1*u; dy=.15-.25*u; a=.45-.75*u
    elif kind=='labor_end': sc=1.045-.014*u+.006*p; dx=.25-.45*u; dy=.06*math.sin(2*math.pi*u); a=-.22+.15*math.sin(math.pi*u)
    else: sc=1.035+.020*u+.004*p; dx=-.25+.55*u; dy=-.08+.15*u; a=.35-.5*u
    fr=camera(bases[idx],sc,dx,dy,a).astype(np.float32)/255
    g=glow_field(t)
    tint=np.array([.08,.19,.30] if idx<2 else [.05,.16,.31],np.float32)
    fr += g[...,None]*tint*(.055+.055*e+.02*p)
    fr *= 1+.015*e+.012*p
    if kind=='threshold_gold':
        h0=int(RH*.70); roi=fr[h0:]; hh=roi.shape[0]
        yy,xx=np.mgrid[0:hh,0:RW].astype(np.float32)
        sh=(1.7*np.sin(yy*.13+t*2.1)*(0.25+.75*e)).astype(np.float32)
        wa=cv2.remap(roi,xx+sh,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        al=((yy/hh)**1.6)[...,None]*.10
        fr[h0:]=roi*(1-al)+wa*al
    fr*=vign
    return np.clip(fr*255,0,255).astype(np.uint8)

def trans(a,b,t,bound,w=.42):
    q=np.clip((t-(bound-w))/(2*w),0,1); s=q*q*(3-2*q)
    sm=(480,270); aa=cv2.resize(a,sm); bb=cv2.resize(b,sm)
    aa=cv2.GaussianBlur(aa,(0,0),0.8+2.0*s); bb=cv2.GaussianBlur(bb,(0,0),2.8-2.0*s)
    m=cv2.addWeighted(aa,1-s,bb,s,0); m=cv2.resize(m,(RW,RH),interpolation=cv2.INTER_LINEAR)
    mid=math.sin(math.pi*s)**2; veil=np.array([16,48,92],np.float32)
    return np.clip(m*(1-.10*mid)+veil*.10*mid,0,255).astype(np.uint8)

silent=OUT/'Silver_Coin_V6_Opening_fast_silent.mp4'
writer=cv2.VideoWriter(str(silent),cv2.VideoWriter_fourcc(*'mp4v'),FPS,(RW,RH))
N=int(round(DUR*FPS)); started=time.time()
for n in range(N):
    t=n/FPS
    idx=max(i for i,(st,_,_,_) in enumerate(SCENES) if st<=t)
    fr=scene(idx,t)
    for b in (10.,20.,30.):
        if abs(t-b)<=.42:
            i2={10.:1,20.:2,30.:3}[b]
            fr=trans(scene(i2-1,t),scene(i2,t),t,b)
            break
    writer.write(fr)
writer.release()
print('render seconds',time.time()-started)
final=OUT/'Silver_Coin_V6_Opening_MusicDirected_720p.mp4'
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(silent),'-i',str(AUDIO),'-t',str(DUR),'-vf',f'scale={DW}:{DH}:flags=lanczos,unsharp=5:5:0.22:3:3:0.0','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(final)],check=True)
