extends Node2D
# 560px source-independent environment-only overlay. Black is additive identity.
# Only far-right sky and sea bands are allowed to change. No source pixels loaded.
var frame_index: int = 0
const W: float = 560.0
const H: float = 560.0

func _process(_delta: float) -> void:
    frame_index += 1
    queue_redraw()

func _draw() -> void:
    draw_rect(Rect2(0.0, 0.0, W, H), Color.BLACK)
    var t: float = float(frame_index) / 24.0
    # Atmospheric motes across rightmost sky. No painting over the subject.
    for i in range(65):
        var u: float = float(i)
        var x: float = 410.0 + fposmod(u * 63.77 + t * (12.0 + float(i % 7) * 2.0), 143.0)
        var y: float = 10.0 + fposmod(u * 41.63 + sin(t * 0.6 + u) * 7.0, 175.0)
        var pulse: float = pow(0.5 + 0.5 * sin(t * 1.8 + u * 1.7), 3.0)
        var radius: float = 0.75 + pulse * 2.9
        draw_circle(Vector2(x, y), radius, Color(0.16 + 0.20 * pulse, 0.42 + 0.27 * pulse, 0.52 + 0.33 * pulse))
    # Animated optical wave highlights restricted to far-right lower water.
    for i in range(28):
        var u: float = float(i)
        var x: float = 410.0 + fposmod(u * 61.0 + sin(t * 1.7 + u * 0.3) * 13.0, 143.0)
        var y: float = 421.0 + fposmod(u * 23.4 + t * (2.5 + float(i % 3)), 120.0)
        var gleam: float = pow(maxf(0.0, sin(t * 2.4 + u * 1.18)), 5.0)
        draw_line(Vector2(x, y), Vector2(minf(W - 3.0, x + 5.0 + gleam * 11.0), y - 1.5), Color(0.14 + gleam * 0.22, 0.30 + gleam * 0.36, 0.37 + gleam * 0.38), 1.0 + gleam * 1.6)
    # Localized, short-lived sky streaks (synthetic optical highlights).
    for j in range(6):
        var u: float = float(j)
        var phase: float = fposmod(t * 0.38 + u * 0.21, 1.0)
        var alpha: float = pow(maxf(0.0, 1.0 - absf(phase - 0.5) * 4.0), 3.0)
        if alpha > 0.04:
            var p := Vector2(418.0 + u * 22.0, 31.0 + u * 21.0)
            draw_line(p, p + Vector2(12.0, 17.0), Color(0.31 * alpha, 0.61 * alpha, 0.68 * alpha), 1.0)
