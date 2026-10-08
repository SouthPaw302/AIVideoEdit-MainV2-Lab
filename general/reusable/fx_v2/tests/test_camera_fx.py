import cv2
import numpy as np

from general.reusable.fx_v2.executor import FXExecutor
from general.reusable.fx_v2.runtime import FXContext
from general.reusable.fx_v2 import promoted_effects as promoted


def synth(width=320,height=180):
    yy,xx=np.mgrid[0:height,0:width]
    im=np.zeros((height,width,3),np.uint8)
    im[...,0]=np.clip(20+xx*190/width,0,255).astype(np.uint8)
    im[...,1]=np.clip(25+yy*180/height,0,255).astype(np.uint8)
    im[...,2]=np.clip(45+(xx+yy)%150,0,255).astype(np.uint8)
    cv2.rectangle(im,(35,35),(120,145),(35,180,240),-1)
    cv2.circle(im,(238,82),38,(210,85,40),-1,cv2.LINE_AA)
    return im


def test_legacy_narrative_camera_default_is_byte_compatible():
    im=synth(); t=.73; duration=2.0
    p=(t/duration)%1.0; ang=np.pi*2*p
    dx=3*np.sin(ang*.5); dy=1.5*np.cos(ang*.5)
    matrix=np.float32([[1,0,dx],[0,1,dy]])
    expected=cv2.warpAffine(im,matrix,(im.shape[1],im.shape[0]),borderMode=cv2.BORDER_REFLECT_101)
    actual=promoted.apply_effect("narrative_camera_travel",im,t,duration,.6,.4)
    assert np.array_equal(actual,expected)


def test_executor_forwards_authored_camera_params():
    im=synth(); ctx=FXContext(t=1.5,duration=2.0,frame_index=36,fps=24)
    params={
        "zoom_start":1.0,
        "zoom_end":1.24,
        "center_start":[.45,.50],
        "center_end":[.56,.47],
        "easing":"smoothstep",
        "zoom_cap":1.40,
    }
    out=FXExecutor().apply_frame("FX2-CAMERA-023",im,ctx,params=params)
    assert out.shape==im.shape and out.dtype==im.dtype
    assert float(np.mean(cv2.absdiff(im,out)))>1.0


def test_authored_camera_clamps_to_source_and_zoom_cap():
    im=synth()
    out=promoted.apply_effect(
        "narrative_camera_travel",im,1.8,2.0,.6,.4,
        params={"zoom_start":.4,"zoom_end":9.0,"center_start":[-4,8],"center_end":[9,-3],"zoom_cap":1.40},
    )
    assert out.shape==im.shape and out.dtype==im.dtype
    assert np.isfinite(out).all()


def test_loopable_orbit_accepts_authored_parameters():
    im=synth()
    params={"rotation_deg":.8,"radius_x_px":3.0,"radius_y_px":1.5,"zoom_base":1.01,"zoom_pulse":.004}
    a=promoted.apply_effect("loopable_eased_orbit",im,.25,2.0,.6,.4,params=params)
    b=promoted.apply_effect("loopable_eased_orbit",im,1.25,2.0,.6,.4,params=params)
    assert a.shape==im.shape and b.shape==im.shape
    assert not np.array_equal(a,b)
