import cv2, numpy as np, wave, argparse, os, math

def audio_envelope(wav_path, fps, nframes, start_sec=0.0):
    with wave.open(wav_path, 'rb') as w:
        sr=w.getframerate(); nch=w.getnchannels(); sw=w.getsampwidth()
        w.setpos(min(int(start_sec*sr), w.getnframes()-1))
        count=min(int((nframes/fps)*sr)+sr, w.getnframes()-w.tell())
        raw=w.readframes(count)
    dtype={1:np.uint8,2:np.int16,4:np.int32}.get(sw,np.int16)
    x=np.frombuffer(raw,dtype=dtype)
    if nch>1: x=x.reshape(-1,nch).mean(axis=1)
    x=x.astype(np.float32)
    if sw==1: x=(x-128)/128.0
    else: x/=float(np.iinfo(dtype).max)
    env=[]
    hop=sr/fps
    for i in range(nframes):
        a=int(i*hop); b=min(len(x), int((i+1)*hop))
        if b<=a: env.append(0.0); continue
        seg=x[a:b]
        env.append(float(np.sqrt(np.mean(seg*seg)+1e-12)))
    env=np.array(env,np.float32)
    if len(env):
        k=max(3,int(fps*0.18)|1)
        env=cv2.GaussianBlur(env.reshape(-1,1),(1,k),0).ravel()
        lo,hi=np.percentile(env,[5,95])
        env=np.clip((env-lo)/(hi-lo+1e-6),0,1)
    return env

def cinematic_restore(frame):
    lab=cv2.cvtColor(frame,cv2.COLOR_BGR2LAB)
    l,a,b=cv2.split(lab)
    clahe=cv2.createCLAHE(clipLimit=1.45,tileGridSize=(8,8))
    l2=clahe.apply(l)
    l=cv2.addWeighted(l,0.58,l2,0.42,0)
    out=cv2.cvtColor(cv2.merge([l,a,b]),cv2.COLOR_LAB2BGR)
    inv=1/0.94
    lut=np.array([min(255,((i/255.0)**inv)*255) for i in range(256)],np.uint8)
    out=cv2.LUT(out,lut)
    f=out.astype(np.float32)
    f[:,:,2]*=1.025; f[:,:,1]*=1.006; f[:,:,0]*=0.985
    f=np.clip(f,0,255).astype(np.uint8)
    hsv=cv2.cvtColor(f,cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:,:,1]*=1.035
    hsv[:,:,1]=np.clip(hsv[:,:,1],0,255)
    f=cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR)
    f=cv2.bilateralFilter(f,5,20,20)
    blur=cv2.GaussianBlur(f,(0,0),1.2)
    return cv2.addWeighted(f,1.10,blur,-0.10,0)

def add_halation(frame, strength):
    lum=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    mask=np.clip((lum-0.72)/0.28,0,1)
    mask=cv2.GaussianBlur(mask,(0,0),10)
    glow=cv2.GaussianBlur(frame,(0,0),12).astype(np.float32)
    out=frame.astype(np.float32)
    alpha=(mask*strength)[...,None]
    glow[:,:,2]*=1.08; glow[:,:,1]*=1.03
    out=out*(1-alpha)+glow*alpha
    return np.clip(out,0,255).astype(np.uint8)

def water_shimmer(frame, t, amount):
    h,w=frame.shape[:2]
    y0=int(h*0.48)
    roi=frame[y0:].copy()
    rh=roi.shape[0]
    yy,xx=np.mgrid[0:rh,0:w].astype(np.float32)
    disp=(1.0+1.6*amount)*np.sin(yy*0.055+t*1.8)+(0.5+0.8*amount)*np.sin(xx*0.018-t*1.2)
    mapx=xx+disp.astype(np.float32)
    mapy=yy+(0.35+0.45*amount)*np.sin(xx*0.025+t*1.35).astype(np.float32)
    warped=cv2.remap(roi,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    alpha=np.linspace(0.0,0.22+0.12*amount,rh,dtype=np.float32)[:,None,None]
    comp=roi.astype(np.float32)*(1-alpha)+warped.astype(np.float32)*alpha
    out=frame.copy(); out[y0:]=np.clip(comp,0,255).astype(np.uint8)
    return out

def process(infile,outfile,wav=None,audio_start=0.0,effects=True):
    cap=cv2.VideoCapture(infile)
    fps=cap.get(cv2.CAP_PROP_FPS) or 30.0
    w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    env=audio_envelope(wav,fps,n,audio_start) if wav else np.zeros(n,np.float32)
    temp=outfile+'.silent.mp4'
    wr=cv2.VideoWriter(temp,cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
    i=0
    while True:
        ok,fr=cap.read()
        if not ok: break
        fr=cinematic_restore(fr)
        if effects:
            e=float(env[i]) if i<len(env) else 0.0
            fr=water_shimmer(fr,i/fps,e)
            fr=add_halation(fr,0.06+0.12*e)
        wr.write(fr); i+=1
    cap.release(); wr.release()
    if wav:
        dur=i/fps
        os.system(f"ffmpeg -y -loglevel error -i '{temp}' -ss {audio_start:.3f} -t {dur:.3f} -i '{wav}' -map 0:v:0 -map 1:a:0 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 256k -shortest '{outfile}'")
        os.remove(temp)
    else:
        os.system(f"ffmpeg -y -loglevel error -i '{temp}' -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p '{outfile}'")
        os.remove(temp)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--wav')
    ap.add_argument('--audio-start',type=float,default=0)
    ap.add_argument('--restore-only',action='store_true')
    a=ap.parse_args()
    process(a.input,a.output,a.wav,a.audio_start,not a.restore_only)
