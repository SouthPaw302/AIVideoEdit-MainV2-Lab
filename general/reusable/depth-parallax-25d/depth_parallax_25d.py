import argparse
import cv2
import math
import numpy as np


def signed_distance_alpha(mask_u8, feather_px=5.0):
    inside = cv2.distanceTransform(mask_u8, cv2.DIST_L2, 5)
    outside = cv2.distanceTransform(255 - mask_u8, cv2.DIST_L2, 5)
    signed = inside - outside
    alpha = np.clip((signed + feather_px) / (2.0 * feather_px), 0.0, 1.0)
    a8 = (alpha * 255).astype(np.uint8)
    a8 = cv2.bilateralFilter(a8, 9, 35, 35)
    return a8.astype(np.float32) / 255.0


def grabcut_subject(image, rect):
    h, w = image.shape[:2]
    mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, mask, rect, bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    binary = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)
    binary = cv2.morphologyEx(
        binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2
    )
    return binary


def inpaint_background(image, subject_mask):
    expanded = cv2.dilate(subject_mask, np.ones((17, 17), np.uint8), iterations=1)
    bg = cv2.inpaint(image, expanded, 7, cv2.INPAINT_TELEA)
    blur = cv2.GaussianBlur(bg, (0, 0), 5)
    edge = cv2.GaussianBlur(expanded, (0, 0), 6).astype(np.float32) / 255.0
    edge = edge[..., None]
    bg = bg.astype(np.float32) * (1.0 - edge * 0.35) + blur.astype(np.float32) * (edge * 0.35)
    return np.clip(bg, 0, 255).astype(np.uint8)


def make_depth_field(image, horizon=0.46, left_foreground=True):
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    depth = np.zeros((h, w), np.float32)
    hy = max(1, min(h - 1, int(h * horizon)))
    depth[:hy] = np.linspace(0.04, 0.10, hy)[:, None]
    depth[hy:] = np.linspace(0.16, 0.52, h - hy)[:, None]
    if left_foreground:
        near = ((yy > h * 0.55) & (xx < w * 0.46)).astype(np.float32)
        near = cv2.GaussianBlur(near, (0, 0), 30)
        depth = np.clip(depth + near * 0.20, 0.0, 1.0)
    return cv2.GaussianBlur(depth, (0, 0), 8)


def warp_depth(image, depth, dx, dy, zoom):
    h, w = image.shape[:2]
    xx, yy = np.meshgrid(
        np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)
    )
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    srcx = (xx - cx) / zoom + cx - dx * depth
    srcy = (yy - cy) / zoom + cy - dy * depth
    return cv2.remap(
        image,
        srcx.astype(np.float32),
        srcy.astype(np.float32),
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101,
    )


def transform_plane(image, alpha, dx, dy, scale):
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D(((w - 1) / 2.0, (h - 1) / 2.0), 0, scale)
    matrix[0, 2] += dx
    matrix[1, 2] += dy
    warped_image = cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT101
    )
    warped_alpha = cv2.warpAffine(
        alpha, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    return warped_image, warped_alpha


def render_25d(image, output, rect, fps=30, seconds=5.0, horizon=0.46, amplitude=10.0):
    h, w = image.shape[:2]
    subject_mask = grabcut_subject(image, rect)
    alpha = signed_distance_alpha(subject_mask, 5.0)
    background = inpaint_background(image, subject_mask)
    depth = make_depth_field(image, horizon=horizon)

    writer = cv2.VideoWriter(
        output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
    )
    total = max(2, int(round(fps * seconds)))

    for i in range(total):
        p = i / (total - 1)
        phase = p * 2.0 * math.pi
        sx = math.sin(phase)
        sy = math.cos(phase)

        dx = amplitude * sx
        dy = amplitude * 0.30 * sy
        zoom = 1.012 + 0.002 * (1.0 - math.cos(phase))

        bg_warped = warp_depth(background, depth, dx, dy, zoom)
        fg_warped, a_warped = transform_plane(
            image,
            alpha,
            dx * 1.55,
            dy * 1.40,
            1.018 + 0.004 * sx,
        )

        soft_shadow = cv2.GaussianBlur(a_warped, (0, 0), 8)
        soft_shadow = np.clip((soft_shadow - a_warped) * 0.12, 0.0, 0.12)[..., None]
        bg_float = bg_warped.astype(np.float32) * (1.0 - soft_shadow)
        out = (
            fg_warped.astype(np.float32) * a_warped[..., None]
            + bg_float * (1.0 - a_warped[..., None])
        )
        writer.write(np.clip(out, 0, 255).astype(np.uint8))

    writer.release()
    return subject_mask, alpha, background, depth


def parse_rect(value):
    vals = [int(v.strip()) for v in value.split(",")]
    if len(vals) != 4:
        raise argparse.ArgumentTypeError("rect must be x,y,w,h")
    return tuple(vals)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("output")
    ap.add_argument("--rect", type=parse_rect, required=True, help="subject rectangle x,y,w,h")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--horizon", type=float, default=0.46)
    ap.add_argument("--amplitude", type=float, default=10.0)
    args = ap.parse_args()

    frame = cv2.imread(args.image)
    if frame is None:
        raise SystemExit(f"Could not read {args.image}")

    render_25d(
        frame,
        args.output,
        args.rect,
        fps=args.fps,
        seconds=args.seconds,
        horizon=args.horizon,
        amplitude=args.amplitude,
    )
