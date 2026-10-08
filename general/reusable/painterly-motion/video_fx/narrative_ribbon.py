#!/usr/bin/env python3
"""Deterministic narrative-ribbon reframing for storyboard/contact-sheet sources.

Use when a storyboard contains several narrow adjacent story panels whose lower
caption band must not enter the moving master. Rather than individually enlarging
small fragments or generatively inpainting text, extract a clean horizontal strip
above the caption band and create overlapping cinematic windows from it.

This preserves real source pixels and makes adjacent shots share geography/color,
which also enables a continuous-pan interpretation.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2


def fit_aspect(im,width,height):
    h,w=im.shape[:2]; target=width/height
    if w/h>target:
        nw=int(h*target);x=max(0,(w-nw)//2);im=im[:,x:x+nw]
    else:
        nh=int(w/target);y=max(0,(h-nh)//2);im=im[y:y+nh]
    return cv2.resize(im,(width,height),interpolation=cv2.INTER_LANCZOS4)


def extract(storyboard,strip_box,centers,window_width,output_dir,width=768,height=432):
    im=cv2.imread(str(storyboard)); x0,y0,x1,y1=strip_box; strip=im[y0:y1,x0:x1]
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);manifest=[]
    for name,cx in centers.items():
        a=max(0,int(cx-window_width/2));b=min(strip.shape[1],a+window_width);a=max(0,b-window_width)
        crop=fit_aspect(strip[:,a:b],width,height)
        crop=cv2.bilateralFilter(crop,5,16,16)
        path=out/f'{name}.jpg';cv2.imwrite(str(path),crop,[cv2.IMWRITE_JPEG_QUALITY,95])
        manifest.append({'name':name,'center_x':cx,'window':[a,b],'path':path.name})
    (out/'narrative-ribbon.json').write_text(json.dumps({'source':str(storyboard),'strip_box':strip_box,'window_width':window_width,'outputs':manifest},indent=2))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('storyboard');ap.add_argument('--strip',required=True,help='x0,y0,x1,y1');ap.add_argument('--centers-json',required=True,help='JSON object of output-name:center-x');ap.add_argument('--window-width',type=int,required=True);ap.add_argument('--output-dir',required=True);ap.add_argument('--width',type=int,default=768);ap.add_argument('--height',type=int,default=432)
    a=ap.parse_args();box=tuple(map(int,a.strip.split(',')));centers=json.loads(Path(a.centers_json).read_text()) if Path(a.centers_json).exists() else json.loads(a.centers_json)
    extract(a.storyboard,box,centers,a.window_width,a.output_dir,a.width,a.height)

if __name__=='__main__':main()
