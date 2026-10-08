#!/usr/bin/env python3
"""Compact CPU neural-radiance-field volume for AIVideoEdit.

This is an actual trained MLP mapping 3D position + view direction to density and
RGB. It is intended as a learned atmospheric/light field for hybrid compositing,
not as a captured-scene photogrammetric reconstruction.

Requires only NumPy.
"""
from __future__ import annotations
import math
import numpy as np

FAMILIES={
 'village': {'fog':(0.34,0.42,0.48),'light':(0.72,0.76,0.74)},
 'threshold': {'fog':(0.40,0.38,0.34),'light':(1.00,0.63,0.26)},
 'tavern': {'fog':(0.43,0.31,0.20),'light':(1.00,0.48,0.16)},
 'coin': {'fog':(0.38,0.40,0.44),'light':(0.88,0.91,0.94)},
 'dawn': {'fog':(0.54,0.46,0.36),'light':(1.00,0.73,0.38)},
}

def fourier(x,bands=4):
    fs=[x]
    for k in range(bands):
        w=(2.0**k)*math.pi; fs.extend([np.sin(w*x),np.cos(w*x)])
    return np.concatenate(fs,axis=-1)

class TinyNeRF:
    def __init__(self,seed=1,hidden=32,bands=4):
        self.rng=np.random.default_rng(seed); self.bands=bands
        din=6*(1+2*bands)
        self.W1=self.rng.normal(0,.18,(din,hidden)).astype(np.float32); self.b1=np.zeros(hidden,np.float32)
        self.W2=self.rng.normal(0,.18,(hidden,4)).astype(np.float32); self.b2=np.zeros(4,np.float32)
    def forward(self,x):
        f=fourier(x,self.bands).astype(np.float32); h=np.tanh(f@self.W1+self.b1); return f,h,h@self.W2+self.b2
    def train(self,x,y,steps=100,lr=.018,batch=1024):
        n=len(x); last=0.0
        for _ in range(steps):
            ii=self.rng.integers(0,n,size=min(batch,n)); xb=x[ii]; yb=y[ii]
            f,h,o=self.forward(xb); err=o-yb; last=float(np.mean(err*err)); d=err*(2.0/len(ii))
            gW2=h.T@d; gb2=d.sum(0); dh=(d@self.W2.T)*(1-h*h); gW1=f.T@dh; gb1=dh.sum(0)
            for g in (gW1,gb1,gW2,gb2):np.clip(g,-2,2,out=g)
            self.W1-=lr*gW1; self.b1-=lr*gb1; self.W2-=lr*gW2; self.b2-=lr*gb2
        return last
    def predict(self,x):
        _,_,o=self.forward(x)
        sigma=np.log1p(np.exp(np.clip(o[:,0],-8,8))); rgb=1/(1+np.exp(-np.clip(o[:,1:4],-8,8)))
        return sigma,rgb

def targets(x,family):
    px,py,pz=x[:,0],x[:,1],x[:,2]; cfg=FAMILIES[family]
    mist=np.exp(-((py+.18)**2)*7.0)*(.35+.65*np.exp(-(pz**2)*1.4))
    plume=np.exp(-((px-.18)**2*4.0+(py+.02)**2*3.0+(pz-.05)**2*1.5))
    shaft=np.exp(-((px+.34)**2*18.0+(py-.08)**2*2.0))*np.exp(-((pz-.15)**2)*.8)
    spark=np.exp(-((px-.48)**2*30.0+(py+.32)**2*24.0+(pz+.18)**2*10.0))
    if family=='coin':
        ring=np.exp(-((np.sqrt(px*px+py*py)-.42)**2)*80.0)*np.exp(-(pz*pz)*2.0); sigma=.35*mist+.35*plume+1.4*ring
    elif family=='village': sigma=.75*mist+.18*plume+.12*shaft
    elif family=='tavern': sigma=.30*mist+.92*plume+.46*shaft+.24*spark
    else: sigma=.45*mist+.48*plume+.62*shaft
    fog=np.array(cfg['fog'],np.float32); light=np.array(cfg['light'],np.float32)
    w=np.clip(shaft[:,None]*.85+spark[:,None]*.6,0,1); rgb=fog[None,:]*(1-w)+light[None,:]*w
    vd=np.clip(x[:,3]*.4-x[:,4]*.2+x[:,5]*.5,-1,1); rgb=np.clip(rgb+(vd[:,None]*.05)*light[None,:],0,1)
    sigma_log=np.log(np.expm1(np.clip(sigma,1e-4,5.0)))[:,None]
    rgb_log=np.log(np.clip(rgb,1e-4,1-1e-4)/(1-np.clip(rgb,1e-4,1-1e-4)))
    return np.concatenate([sigma_log,rgb_log],axis=1).astype(np.float32)

def train_family(family,seed=302,samples=7000,steps=100):
    rng=np.random.default_rng(seed+sum(map(ord,family)))
    pos=rng.uniform(-1,1,(samples,3)).astype(np.float32)
    vd=rng.normal(size=(samples,3)).astype(np.float32); vd/=np.linalg.norm(vd,axis=1,keepdims=True)+1e-8
    x=np.concatenate([pos,vd],axis=1); y=targets(x,family)
    net=TinyNeRF(seed=seed+len(family)); train_loss=net.train(x,y,steps=steps)
    vr=np.random.default_rng(seed+999+len(family)); vp=vr.uniform(-1,1,(1200,3)).astype(np.float32); vv=vr.normal(size=(1200,3)).astype(np.float32); vv/=np.linalg.norm(vv,axis=1,keepdims=True)+1e-8
    vx=np.concatenate([vp,vv],axis=1); vy=targets(vx,family); _,_,vo=net.forward(vx); val=float(np.mean((vo-vy)**2))
    return net,{'family':family,'seed':seed,'samples':samples,'steps':steps,'train_mse':train_loss,'validation_mse':val}

def render_rgba(net,w=128,h=72,samples=22,phase=0.0,max_alpha=.50):
    xs=np.linspace(-1,1,w,dtype=np.float32); ys=np.linspace(-1,1,h,dtype=np.float32); X,Y=np.meshgrid(xs,ys)
    camx=.08*math.sin(2*math.pi*phase); camy=.04*math.cos(2*math.pi*phase)
    acc=np.zeros((h,w,3),np.float32); trans=np.ones((h,w),np.float32); zvals=np.linspace(-1,1,samples,dtype=np.float32); step=2.0/samples
    for z in zvals:
        px=X+camx*(.6+.4*z); py=Y+camy*(.5+.5*z); pz=np.full_like(X,z)
        dirs=np.stack([X*.45,Y*.45,np.ones_like(X)],axis=-1); dirs/=np.linalg.norm(dirs,axis=-1,keepdims=True)+1e-8
        inp=np.concatenate([np.stack([px,py,pz],axis=-1),dirs],axis=-1).reshape(-1,6)
        sig,rgb=net.predict(inp); sig=sig.reshape(h,w); rgb=rgb.reshape(h,w,3)
        alpha=1-np.exp(-sig*step*.62); weight=trans*alpha; acc+=weight[...,None]*rgb; trans*=1-alpha
    a=np.clip(1-trans,0,max_alpha)
    return np.dstack([np.clip(acc,0,1),a]).astype(np.float32)
