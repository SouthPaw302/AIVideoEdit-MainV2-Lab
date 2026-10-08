from __future__ import annotations
import math
import cv2
import numpy as np

TAU = math.tau

# Effect-centric production names. Historical project labels are aliases only.
EFFECT_NAMES = [
    'pseudo_depth_field','localized_micro_warp','mesh_breath','transient_warp','narrative_camera_travel',
    'firelight_breath','wet_reflection_ripple','puddle_shimmer','heat_haze','volumetric_light_shafts',
    'radial_light_shafts','chroma_pigment_transport','fog_pigment_travel','object_portal','warm_halation_bloom',
    'water_region_displacement_shimmer','rms_memory_modulation','disocclusion_alpha_feather','loopable_eased_orbit',
    'rain_puddle_ember_composite','threshold_reflection_lamp_flicker','forge_motion_furnace_sparks','smoke_memory_forms',
    'ember_crack_light_reveal','parallax_fog_cloth_fire_decay','steam_fog_cloth_horizon_gold','rotating_architecture_debris',
    'corridor_push_focus_definition','reflection_ash_dawn','radial_waveform_ember_bursts','temporal_grade_shift',
    'rack_focus_heat_pulse','runic_oscilloscope','radial_frequency_ring','spectrum_energy_flame','waveform_smoke_trails',
    'particle_tunnel','feedback_plasma_gravity_inversion','raindrop_to_ember','ember_to_sun','structural_morph_transition',
    'smoke_to_storm_clouds','reflection_to_water','fire_to_lightning','glint_to_orb','wet_road_rain_reflection',
    'candlelight_micro_loop','atmospheric_fog','ghosted_memory_transition','crowd_sway','forest_breath','impact_pulse'
]

LEGACY_ALIASES = {
 'Pseudo-depth field':'pseudo_depth_field','Depth parallax':'pseudo_depth_field','Compact NeRF volume':'pseudo_depth_field',
 'Hybrid neural-radiance-field spatial rendering':'pseudo_depth_field','Localized micro-warp':'localized_micro_warp','Mesh breath':'mesh_breath',
 'Temporal canvas lock':'localized_micro_warp','Depth-focus breath':'mesh_breath','Performance transient warp':'transient_warp',
 'Narrative-ribbon camera travel':'narrative_camera_travel','Advected atmosphere':'atmospheric_fog','Motivated rain / embers':'rain_puddle_ember_composite',
 'Firelight breath':'firelight_breath','Wet reflection ripple':'wet_reflection_ripple','Puddle shimmer':'puddle_shimmer','Heat haze':'heat_haze',
 'Depth-gated volumetric light shafts':'volumetric_light_shafts','Candle/window radial shafts':'radial_light_shafts','Localized specular glint':'glint_to_orb',
 'Chroma pigment transport':'chroma_pigment_transport','Pigment dissolve':'chroma_pigment_transport','Fog/pigment travel':'fog_pigment_travel',
 'Object / coin portal':'object_portal','Forest breath / hair / garland':'forest_breath','Coin glint':'glint_to_orb',
 'Tavern firelight / smoke':'firelight_breath','Fiddler impact':'impact_pulse','Communal crowd sway':'crowd_sway',
 'Lightning / wet reflection':'wet_road_rain_reflection','Gaussian-style light shafts':'volumetric_light_shafts','Fog / pigment travel':'fog_pigment_travel',
 'Source-derived motion loop candidate':'localized_micro_warp','Selective warm halation / bloom':'warm_halation_bloom',
 'Water-region displacement / shimmer':'water_region_displacement_shimmer','RMS-driven memory modulation':'rms_memory_modulation',
 'Continuous soft-depth 2.5D':'pseudo_depth_field','Inpainted disocclusion plate + signed-distance alpha feather':'disocclusion_alpha_feather',
 'Loopable eased orbit path':'loopable_eased_orbit','Visible Memory FX preset':'ghosted_memory_transition',
 'Isolated rain planes + puddle ripple + weak ember pulse':'rain_puddle_ember_composite','Threshold reflection + lamp flicker':'threshold_reflection_lamp_flicker',
 'Forge micro-motion + furnace breath + onset sparks':'forge_motion_furnace_sparks','Smoke-hand memory forms':'smoke_memory_forms',
 'Ember-crack light reveals in architecture':'ember_crack_light_reveal','Parallax + fog drift + cloak/wolf gait micro-loops + fire decay':'parallax_fog_cloth_fire_decay',
 'Steam/fog + grass/cloak movement + horizon-gold growth':'steam_fog_cloth_horizon_gold','Rotating architecture + suspended debris + pressure-synced scale':'rotating_architecture_debris',
 'Deep corridor push + long focus pull + definition gain':'corridor_push_focus_definition','Locked reflection + ash fall + ember-to-dawn transformation':'reflection_ash_dawn',
 'Radial forged waveform + transient ember bursts':'radial_waveform_ember_bursts','Storm-blue to dawn-gold temporal grade':'temporal_grade_shift',
 'Symbolic mark→heroine rack focus + final heat pulse':'rack_focus_heat_pulse','Runic oscilloscope':'runic_oscilloscope',
 'Radial frequency ring around iron sigil':'radial_frequency_ring','Spectrum energy inside forge flame':'spectrum_energy_flame',
 'Waveform trails in smoke':'waveform_smoke_trails','Particle tunnel between impossible spaces':'particle_tunnel',
 'Feedback/plasma gravity-inversion passage':'feedback_plasma_gravity_inversion','raindrop→ember':'raindrop_to_ember','ember→sun':'ember_to_sun',
 'doorway→corridor':'structural_morph_transition','iron railing→tree branches':'structural_morph_transition','smoke→storm clouds':'smoke_to_storm_clouds',
 'reflection→underground water':'reflection_to_water','fire→lightning':'fire_to_lightning','eye/glint→moon or forge light':'glint_to_orb',
 'Living-image animation':'localized_micro_warp','Wet-road / rain-reflection animation':'wet_road_rain_reflection','Candlelight micro-loop':'candlelight_micro_loop',
 'Atmospheric fog':'atmospheric_fog','Restrained ancestral-ghost transition':'ghosted_memory_transition'
}

def _phase(t,d): return (float(t)/max(float(d),1e-6))%1.0

def _grid(im):
    h,w=im.shape[:2]; y,x=np.mgrid[0:h,0:w].astype(np.float32); return y,x

def _remap(im,dx,dy):
    y,x=_grid(im); return cv2.remap(im,x+dx.astype(np.float32),y+dy.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def _blend(a,b,alpha):
    if np.isscalar(alpha): return cv2.addWeighted(a,1-float(alpha),b,float(alpha),0)
    alpha=np.clip(alpha,0,1).astype(np.float32)[...,None]
    return np.clip(a.astype(np.float32)*(1-alpha)+b.astype(np.float32)*alpha,0,255).astype(np.uint8)

def _blur_mask(h,w,cx=.5,cy=.5,rx=.3,ry=.3):
    y,x=np.mgrid[0:h,0:w].astype(np.float32); q=((x/w-cx)/max(rx,1e-3))**2+((y/h-cy)/max(ry,1e-3))**2
    return np.exp(-2.2*q).astype(np.float32)

def _noise(h,w,seed,scale=18):
    rng=np.random.default_rng(seed); a=rng.random((max(4,h//scale),max(4,w//scale)),dtype=np.float32)
    return cv2.GaussianBlur(cv2.resize(a,(w,h),interpolation=cv2.INTER_CUBIC),(0,0),3)

def _rain(im,t,strength=.5):
    out=im.copy(); h,w=im.shape[:2]; rng=np.random.default_rng(302); pts=rng.random((max(12,int(85*strength)),4))
    for x0,y0,sp,l in pts:
        x=int((x0*w+t*(10+30*sp))%w); y=int((y0*h+t*(130+90*sp))%h); L=int(7+18*l)
        cv2.line(out,(x,y),(max(0,x-3),min(h-1,y+L)),(175,185,200),1,cv2.LINE_AA)
    return out

def _embers(im,t,strength=.5):
    out=im.copy(); h,w=im.shape[:2]; rng=np.random.default_rng(303); pts=rng.random((max(10,int(45*strength)),4))
    for x0,y0,sp,ph in pts:
        x=int((x0*w+8*math.sin(t*(.8+sp)+ph*TAU))%w); y=int((y0*h-t*(18+32*sp))%h)
        r=1+int(2*max(0,math.sin(t*2+ph*TAU))); cv2.circle(out,(x,y),r,(20,110,245),-1,cv2.LINE_AA)
    return out

def _fog(im,t,strength=.4):
    h,w=im.shape[:2]; n=_noise(h,w,304); M=np.float32([[1,0,18*math.sin(t*.37)],[0,1,-8*t]])
    n=cv2.warpAffine(n,M,(w,h),borderMode=cv2.BORDER_WRAP); a=np.clip((n-.42)*strength,0,.18)
    tint=np.full_like(im,(118,122,130)); return _blend(im,tint,a)

def _glow(im,cx,cy,strength,color=(45,125,255)):
    h,w=im.shape[:2]; m=_blur_mask(h,w,cx,cy,.22,.26)*float(strength)
    glow=np.zeros_like(im); glow[:]=color; return _blend(im,glow,np.clip(m*.5,0,.55))

def _transition(a,b,p):
    q=.5-.5*math.cos(np.clip(p,0,1)*math.pi); return cv2.addWeighted(a,1-q,b,q,0)

def _pair_param(value, default):
    if isinstance(value,(list,tuple)) and len(value)==2:
        return float(value[0]),float(value[1])
    return float(default[0]),float(default[1])

def _authored_camera(im,p,params,default_zoom_start=1.0,default_zoom_end=1.10,default_center_start=(.5,.5),default_center_end=(.5,.5)):
    """Bounded source-locked crop/resize camera move. No pixels are invented."""
    h,w=im.shape[:2]; q=float(np.clip(p,0,1)); easing=str(params.get("easing","smoothstep")).lower()
    if easing=="smoothstep": q=q*q*(3-2*q)
    elif easing=="cosine": q=.5-.5*math.cos(math.pi*q)
    elif easing!="linear": raise ValueError(f"unsupported camera easing: {easing}")
    cap=float(np.clip(params.get("zoom_cap",1.40),1.0,1.50))
    z0=float(np.clip(params.get("zoom_start",default_zoom_start),1.0,cap)); z1=float(np.clip(params.get("zoom_end",default_zoom_end),1.0,cap))
    c0=_pair_param(params.get("center_start"),default_center_start); c1=_pair_param(params.get("center_end"),default_center_end)
    z=z0+(z1-z0)*q; cx=c0[0]+(c1[0]-c0[0])*q; cy=c0[1]+(c1[1]-c0[1])*q
    cw=max(2,min(w,int(round(w/z)))); ch=max(2,min(h,int(round(h/z))))
    halfx=cw/(2.0*w); halfy=ch/(2.0*h); cx=float(np.clip(cx,halfx,1-halfx)); cy=float(np.clip(cy,halfy,1-halfy))
    x0=max(0,min(w-cw,int(round(cx*w-cw/2)))); y0=max(0,min(h-ch,int(round(cy*h-ch/2))))
    crop=im[y0:y0+ch,x0:x0+cw]
    return cv2.resize(crop,(w,h),interpolation=cv2.INTER_LANCZOS4)

def apply_effect(name:str, frame:np.ndarray, t:float, duration:float=2.0, energy:float=.6, transient:float=.4, second_frame:np.ndarray|None=None, params:dict|None=None)->np.ndarray:
    if name not in EFFECT_NAMES: raise KeyError(name)
    im=frame.copy(); h,w=im.shape[:2]; y,x=_grid(im); p=_phase(t,duration); ang=TAU*p
    b = second_frame.copy() if second_frame is not None else cv2.GaussianBlur(255-im,(0,0),1.2)
    if name=='pseudo_depth_field':
        dx=(x-w*.5)/max(w,1)*3.2*math.sin(ang); dy=(y-h*.5)/max(h,1)*2.0*math.sin(ang+.8); return _remap(im,dx,dy)
    if name=='localized_micro_warp':
        m=_blur_mask(h,w,.5,.53,.42,.42); dx=m*(1.4*np.sin(y/24+ang)); dy=m*(.9*np.sin(x/31-ang)); return _blend(im,_remap(im,dx,dy),m*.7)
    if name=='mesh_breath':
        s=1+.012*math.sin(ang); M=cv2.getRotationMatrix2D((w/2,h/2),0,s); return cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101)
    if name=='transient_warp':
        amp=(.5+2.4*transient)*math.sin(ang*2); dx=amp*np.sin(y/18); return _remap(im,dx,np.zeros_like(dx))
    if name=='narrative_camera_travel':
        if params:
            return _authored_camera(im,p,params,1.0,1.10,(.50,.50),(.52,.49))
        dx=3*math.sin(ang*.5); dy=1.5*math.cos(ang*.5); M=np.float32([[1,0,dx],[0,1,dy]]); return cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101)
    if name=='firelight_breath': return _glow(im,.24,.68,.7+.25*math.sin(ang),(20,95,245))
    if name in {'wet_reflection_ripple','puddle_shimmer','water_region_displacement_shimmer','reflection_to_water'}:
        m=np.clip((y/h-.52)/.48,0,1); dx=m*(2.2*np.sin(y/6+ang*2)+1.1*np.sin(x/29-ang)); out=_remap(im,dx,np.zeros_like(dx)); return _blend(im,out,m*.45)
    if name=='heat_haze':
        m=_blur_mask(h,w,.5,.55,.5,.5); dx=m*2.5*np.sin(y/7+ang); return _blend(im,_remap(im,dx,np.zeros_like(dx)),m*.65)
    if name in {'volumetric_light_shafts','radial_light_shafts'}:
        out=im.astype(np.float32); cx,cy=.18*w,.12*h; d=np.sqrt((x-cx)**2+(y-cy)**2); rays=np.maximum(0,np.sin(np.arctan2(y-cy,x-cx)*9+ang))*(1-d/np.sqrt(w*w+h*h)); rays=np.clip(rays,0,1)*18; out+=rays[...,None]*np.array([.55,.75,1.0]); return np.clip(out,0,255).astype(np.uint8)
    if name in {'chroma_pigment_transport','fog_pigment_travel'}:
        q=(.5-.5*math.cos(ang)); hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV).astype(np.float32); hsv[...,0]=(hsv[...,0]+10*q)%180; out=cv2.cvtColor(np.uint8(np.clip(hsv,0,255)),cv2.COLOR_HSV2BGR); return _fog(out,t,.25) if name=='fog_pigment_travel' else out
    if name=='object_portal':
        m=_blur_mask(h,w,.5,.5,.20,.30); return _blend(im,b,m*(.45+.35*math.sin(ang)**2))
    if name=='warm_halation_bloom':
        br=cv2.GaussianBlur(im,(0,0),5); warm=np.clip(br.astype(np.float32)*np.array([.95,1.02,1.13]),0,255).astype(np.uint8); return cv2.addWeighted(im,.76,warm,.24+.08*math.sin(ang),0)
    if name=='rms_memory_modulation':
        ghost=cv2.GaussianBlur(im,(0,0),2.5); return cv2.addWeighted(im,.82-.08*energy,ghost,.18+.08*energy,4*math.sin(ang))
    if name=='disocclusion_alpha_feather':
        shifted=np.roll(im,int(4*math.sin(ang)),axis=1); m=cv2.GaussianBlur(_blur_mask(h,w,.5,.5,.45,.45),(0,0),7); return _blend(im,shifted,m*.22)
    if name=='loopable_eased_orbit':
        if params:
            rot=float(params.get("rotation_deg",.55)); rx=float(params.get("radius_x_px",2.0)); ry=float(params.get("radius_y_px",1.2))
            zoom=float(params.get("zoom_base",1.006))+float(params.get("zoom_pulse",.006))*math.cos(ang)
            M=cv2.getRotationMatrix2D((w/2,h/2),rot*math.sin(ang),zoom); M[:,2]+=[rx*math.cos(ang),ry*math.sin(ang)]
            return cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101)
        M=cv2.getRotationMatrix2D((w/2,h/2),.55*math.sin(ang),1+.006*math.cos(ang)); M[:,2]+=[2*math.cos(ang),1.2*math.sin(ang)]; return cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101)
    if name=='rain_puddle_ember_composite': return _embers(_rain(apply_effect('puddle_shimmer',im,t,duration,energy,transient),t,.35),t,.28)
    if name=='threshold_reflection_lamp_flicker': return _glow(apply_effect('wet_reflection_ripple',im,t,duration,energy,transient),.25,.35,.5+.2*math.sin(ang*3),(25,115,245))
    if name=='forge_motion_furnace_sparks': return _embers(_glow(apply_effect('localized_micro_warp',im,t,duration,energy,transient),.5,.75,.8,(20,95,255)),t,.55)
    if name=='smoke_memory_forms': return _fog(_blend(im,b,_blur_mask(h,w,.55,.42,.25,.34)*.13*(.5+.5*math.sin(ang))),t,.35)
    if name=='ember_crack_light_reveal':
        out=_embers(im,t,.32); lines=(np.sin((x+y)/18+ang*2)>.985).astype(np.float32); hot=np.full_like(im,(15,120,255)); return _blend(out,hot,cv2.GaussianBlur(lines,(0,0),1.5)*.28)
    if name=='parallax_fog_cloth_fire_decay': return _fog(_embers(apply_effect('pseudo_depth_field',im,t,duration,energy,transient),t,.18*(1-p)),t,.25)
    if name=='steam_fog_cloth_horizon_gold':
        out=_fog(apply_effect('localized_micro_warp',im,t,duration,energy,transient),t,.32); grad=np.clip((1-y/h)*p,0,1)*.22; gold=np.full_like(im,(30,155,245)); return _blend(out,gold,grad)
    if name=='rotating_architecture_debris':
        M=cv2.getRotationMatrix2D((w/2,h/2),1.2*math.sin(ang),1+.006*math.sin(ang)); out=cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101); return _embers(out,t,.12)
    if name=='corridor_push_focus_definition':
        if params:
            out=_authored_camera(im,p,params,1.0,1.08,(.50,.50),(.52,.48)); sharp=cv2.detailEnhance(out,sigma_s=10,sigma_r=.15)
            amount=float(np.clip(params.get("definition_strength",.25),0,.50))*p; return cv2.addWeighted(out,1-amount,sharp,amount,0)
        s=1+.025*p; M=cv2.getRotationMatrix2D((w/2,h/2),0,s); out=cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101); sharp=cv2.detailEnhance(out,sigma_s=10,sigma_r=.15); return cv2.addWeighted(out,1-p*.25,sharp,p*.25,0)
    if name=='reflection_ash_dawn':
        out=apply_effect('wet_reflection_ripple',im,t,duration,energy,transient); out=_embers(out,-t,.20*(1-p)); gold=np.full_like(im,(35,150,235)); return _blend(out,gold,np.full((h,w),.18*p,np.float32))
    if name in {'radial_waveform_ember_bursts','runic_oscilloscope','radial_frequency_ring','spectrum_energy_flame'}:
        out=im.copy(); c=(w//2,h//2); base=int(min(h,w)*(.18+.03*math.sin(ang*3)))
        if name=='runic_oscilloscope':
            pts=[(i,int(h*.55+12*math.sin(i/11+ang*3)*(0.4+energy))) for i in range(w)]; cv2.polylines(out,[np.array(pts,np.int32)],False,(70,220,255),1,cv2.LINE_AA); return out
        for k in range(2 if name!='spectrum_energy_flame' else 4): cv2.circle(out,c,base+8*k,(25,130+20*k,245),1,cv2.LINE_AA)
        return _embers(out,t,.32) if name=='radial_waveform_ember_bursts' else out
    if name=='waveform_smoke_trails':
        out=_fog(im,t,.28); pts=np.array([(i,int(h*.5+15*math.sin(i/15+ang*2))) for i in range(w)],np.int32); cv2.polylines(out,[pts],False,(120,180,205),1,cv2.LINE_AA); return out
    if name=='particle_tunnel':
        out=im.copy(); c=np.array([w*.5,h*.5]); rng=np.random.default_rng(501)
        for a0,r0 in rng.random((65,2)):
            a=a0*TAU+ang*.6; r=(r0+p)%1; pt=(int(c[0]+math.cos(a)*r*w*.48),int(c[1]+math.sin(a)*r*h*.48)); cv2.circle(out,pt,1,(160,200,245),-1)
        return out
    if name=='feedback_plasma_gravity_inversion':
        hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV); hsv[...,0]=(hsv[...,0].astype(np.int16)+int(35*math.sin(ang)))%180; out=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR); dy=3*np.sin(x/20+ang); return _remap(out,np.zeros_like(dy),dy)
    if name=='temporal_grade_shift':
        a=p; f=im.astype(np.float32); f[...,0]*=1+.22*(1-a); f[...,2]*=1+.28*a; f[...,1]*=1+.06*a; return np.clip(f,0,255).astype(np.uint8)
    if name=='rack_focus_heat_pulse':
        blur=cv2.GaussianBlur(im,(0,0),3*(1-p)+.1); m=_blur_mask(h,w,.55,.48,.22,.32); out=_blend(blur,im,m*(.55+.45*p)); return _glow(out,.55,.48,.28*math.sin(ang)**2,(15,90,245))
    if name=='raindrop_to_ember': return _transition(_rain(im,t,.45),_embers(im,t,.45),p)
    if name=='ember_to_sun': return _transition(_embers(im,t,.45),_glow(im,.72,.22,1.0,(20,160,255)),p)
    if name=='structural_morph_transition':
        dx=4*math.sin(math.pi*p)*np.sin(y/20); return _transition(_remap(im,dx,np.zeros_like(dx)),b,p)
    if name=='smoke_to_storm_clouds': return _transition(_fog(im,t,.42),_fog(b,t+.7,.62),p)
    if name=='fire_to_lightning': return _transition(_glow(im,.35,.7,.75,(15,95,255)),_glow(b,.72,.15,1.0,(210,220,255)),p)
    if name=='glint_to_orb': return _glow(_transition(im,b,p),.55,.45,.55+.4*p,(170,220,255))
    if name=='wet_road_rain_reflection': return _rain(apply_effect('wet_reflection_ripple',im,t,duration,energy,transient),t,.5)
    if name=='candlelight_micro_loop': return _glow(im,.25,.55,.42+.18*math.sin(ang*3),(20,105,245))
    if name=='atmospheric_fog': return _fog(im,t,.42)
    if name=='ghosted_memory_transition':
        shifted=np.roll(b,int(3*math.sin(ang)),axis=1); return _blend(im,shifted,np.full((h,w),.12+.20*math.sin(math.pi*p),np.float32))
    if name=='crowd_sway': return _remap(im,1.8*np.sin(y/28+ang),np.zeros_like(y))
    if name=='forest_breath': return _fog(apply_effect('localized_micro_warp',im,t,duration,energy,transient),t,.16)
    if name=='impact_pulse':
        M=cv2.getRotationMatrix2D((w/2,h/2),0,1+.018*math.sin(ang*2)*(.4+transient)); return cv2.warpAffine(im,M,(w,h),borderMode=cv2.BORDER_REFLECT_101)
    raise KeyError(name)
