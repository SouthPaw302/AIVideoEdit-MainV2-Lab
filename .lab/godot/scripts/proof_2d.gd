extends Node2D
# Deterministic procedural graphics fixture. Not production video or approved media.
var frame: int = 0

func _process(_delta: float) -> void:
    frame += 1
    queue_redraw()

func _draw() -> void:
    var t: float = float(frame) / 24.0
    # Layered dawn sky (no source media / no generated stills).
    for i in range(24):
        var y: float = float(i) * 15.0
        var shade: float = float(i) / 24.0
        draw_rect(Rect2(0.0, y, 640.0, 15.0), Color(0.035 + shade * 0.10, 0.065 + shade * 0.13, 0.15 + shade * 0.14))
    draw_circle(Vector2(455.0 + sin(t * 0.45) * 12.0, 94.0), 42.0, Color(0.99, 0.74, 0.43, 0.9))
    draw_circle(Vector2(455.0 + sin(t * 0.45) * 12.0, 94.0), 62.0, Color(0.99, 0.62, 0.31, 0.07))
    # Fixed geometry with camera-like parallax generated from coordinates.
    var shift_far: float = sin(t * 0.7) * 11.0
    var far_points := PackedVector2Array([
        Vector2(-40.0 + shift_far, 310.0), Vector2(40.0 + shift_far, 193.0),
        Vector2(153.0 + shift_far, 259.0), Vector2(305.0 + shift_far, 140.0),
        Vector2(446.0 + shift_far, 243.0), Vector2(570.0 + shift_far, 183.0),
        Vector2(700.0 + shift_far, 318.0)
    ])
    draw_colored_polygon(far_points, Color(0.17, 0.29, 0.33))
    var shift_near: float = sin(t * 0.95) * 22.0
    var near_points := PackedVector2Array([
        Vector2(-50.0 + shift_near, 360.0), Vector2(78.0 + shift_near, 273.0),
        Vector2(183.0 + shift_near, 315.0), Vector2(344.0 + shift_near, 241.0),
        Vector2(518.0 + shift_near, 313.0), Vector2(695.0 + shift_near, 261.0),
        Vector2(700.0 + shift_near, 370.0)
    ])
    draw_colored_polygon(near_points, Color(0.06, 0.18, 0.20))
    # Moving firefly particles and ribbons prove non-frozen frames.
    for i in range(34):
        var x: float = fposmod(float(i * 83) + t * (15.0 + float(i % 5) * 5.0), 660.0) - 10.0
        var y: float = 177.0 + fposmod(float(i * 31), 151.0) + sin(t * 2.0 + float(i)) * 10.0
        draw_circle(Vector2(x, y), 1.3 + float(i % 3), Color(0.85, 0.97, 0.68, 0.30 + 0.12 * float(i % 3)))
    draw_line(Vector2(0.0, 336.0 + sin(t) * 5.0), Vector2(640.0, 325.0 + sin(t) * 5.0), Color(0.44, 0.82, 0.72, 0.38), 3.0)
    draw_string(ThemeDB.fallback_font, Vector2(16.0, 27.0), "GODOT / 2D TECHNICAL MOVIE TEST", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color.WHITE)
    draw_string(ThemeDB.fallback_font, Vector2(16.0, 348.0), "SYNTHETIC FIXTURE - NOT PRODUCTION MEDIA", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.9, 0.94, 0.97))
