extends Node2D
# Independent authored cinematic: actual source painting + measured musical movement.
const WIDTH: float = 960.0
const HEIGHT: float = 540.0
const FPS: int = 24
const FRAMES: int = 336
var texture: Texture2D
var energy: Array = []
var onset: Array = []
var frame_index: int = 0

func _ready() -> void:
    texture = load("res://assets/backdrop.png") as Texture2D
    var f: FileAccess = FileAccess.open("res://data/audio_drive.json", FileAccess.READ)
    if texture == null or f == null:
        push_error("Source painting or verified music controls unavailable; refusing fallback.")
        get_tree().quit(1)
        return
    var parsed: Variant = JSON.parse_string(f.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        push_error("Invalid PCM music controls.")
        get_tree().quit(1)
        return
    energy = parsed.get("energy", [])
    onset = parsed.get("onset", [])
    if energy.size() != FRAMES or onset.size() != FRAMES:
        push_error("Frame-aligned music controls missing.")
        get_tree().quit(1)

func _process(_delta: float) -> void:
    frame_index += 1
    queue_redraw()

func _value(t: float, values: Array) -> float:
    var times: Array = [0.0, 2.6, 5.1, 8.3, 11.1, 14.0]
    for i in range(times.size()-1):
        if t <= float(times[i+1]):
            var p: float = clampf((t-float(times[i])) / (float(times[i+1])-float(times[i])), 0.0, 1.0)
            p = p*p*(3.0-2.0*p)
            return lerpf(float(values[i]), float(values[i+1]), p)
    return float(values[values.size()-1])

func _background(t: float, e: float) -> void:
    var wh: Vector2 = texture.get_size()
    var iw: float = wh.x
    var ih: float = wh.y
    var cw: float = iw
    var ch: float = ih
    if iw/ih > WIDTH/HEIGHT:
        cw = ih*WIDTH/HEIGHT
    else:
        ch = iw*HEIGHT/WIDTH
    var zoom: float = _value(t,[1.22,1.15,1.03,1.08,1.16,1.08]) + e*0.003
    cw /= zoom
    ch /= zoom
    var dx: float = _value(t,[-0.07,-0.03,0.0,0.035,0.08,0.02])
    var dy: float = _value(t,[-0.01,-0.005,0.0,0.014,0.025,0.0])
    var cx: float = iw*0.5+dx*iw
    var cy: float = ih*0.5+dy*ih
    var src := Rect2(clampf(cx-cw/2.0,0.0,iw-cw),clampf(cy-ch/2.0,0.0,ih-ch),cw,ch)
    draw_texture_rect_region(texture,Rect2(0.0,0.0,WIDTH,HEIGHT),src)
    draw_rect(Rect2(0.0,0.0,WIDTH,HEIGHT),Color(0.075,0.09,0.12,0.08))

func _lighting(t: float, e: float, beat: float) -> void:
    var center := Vector2(WIDTH*.59+sin(t*.4)*6.0,HEIGHT*.42)
    var power: float = .65+.35*e+.23*beat
    for ring in range(23,0,-1):
        var q: float = float(ring)/23.0
        draw_circle(center,16.0+q*200.0,Color(1.0,.55,.20,.0042*(1.0-q)*power))
    for i in range(15):
        var x: float = 65.0+float(i)*64.0
        var y: float = 126.0+float(i%5)*42.0
        var pulse: float = .5+.5*sin(t*.8+float(i)*1.9)
        draw_circle(Vector2(x+sin(t*.48+float(i))*.8,y+cos(t*.31+float(i))*.8),1.2+3.1*pulse,Color(1.0,.77,.43,(.02+.07*beat)*pulse))

func _air(t: float, e: float, beat: float) -> void:
    # Three depth layers, each physically distinct in drift speed and size.
    for i in range(165):
        var k: float = float(i)
        var depth: float = .34+float(i%5)*.14
        var vel: float = (4.0+float(i%7)*2.8)*depth
        var x: float = fposmod(k*113.37+sin(k*17.3)*115.0+t*vel,WIDTH+70.0)-35.0
        var y: float = fposmod(k*79.31+cos(k*11.4)*77.0-t*vel*.48,HEIGHT+70.0)-35.0
        var flicker: float = pow(maxf(0.0,.5+.5*sin(t*(.8+depth)+k*2.2)),2.0)
        var radius: float = (.65+float(i%4)*.62)*depth*(1.0+.25*beat)
        var alpha: float = (.08+.23*flicker)*(.35+.65*e)
        draw_circle(Vector2(x,y),radius*2.7,Color(1.0,.53,.28,alpha*.13))
        draw_circle(Vector2(x,y),radius,Color(1.0,.83,.57,alpha))
    # The 8-13 second wind gust is created by Godot from geometry, not video loops.
    if t>=7.5 and t<13.3:
        var wind: float = pow(maxf(0.0,sin((t-7.5)*1.22)),3.0)
        for i in range(32):
            var k: float = float(i)
            var x: float = fposmod(k*103.0+t*137.0+sin(k*2.0)*53.0,WIDTH+210.0)-100.0
            var y: float = 20.0+k*16.1
            draw_line(Vector2(x,y),Vector2(x+13.0+float(i%4)*8.0,y-7.0),Color(.87,.81,.60,.08*wind*(.5+e)),1.0)

func _haze(t: float, e: float) -> void:
    for band in range(3):
        var level: float = 415.0+float(band)*42.0
        for i in range(20):
            var k: float = float(i)
            var x: float = -15.0+k*52.0+sin(t*(.26+float(band)*.07)+k*.55)*20.0
            var y: float = level+sin(k*.67+t*.51)*11.0
            draw_circle(Vector2(x,y),42.0+float(i%5)*10.0,Color(.62,.71,.65,(.003+.002*e)*(1.0-float(band)*.2)))
    for i in range(9):
        var k: float = float(i)
        draw_line(Vector2(0.0,500.0+k*4.0+sin(t*.7+k*.3)*3.0),Vector2(WIDTH,500.0+k*4.0),Color(.59,.63,.57,.014*(1.0-k/10.0)),2.0)

func _foreground(t: float, e: float) -> void:
    # Side-only authored branch silhouettes produce strong depth parallax.
    for side in range(2):
        var left: bool = side == 0
        var dir: float = 1.0 if left else -1.0
        var base: float = -28.0 if left else WIDTH+28.0
        for branch in range(5):
            var b: float = float(branch)
            var sway: float = sin(t*.62+b*.87)*(8.0+b*2.0)*(.8+.2*e)
            var poly := PackedVector2Array()
            for step in range(13):
                var q: float = float(step)/12.0
                poly.push_back(Vector2(base+dir*(39.0+b*20.0)*q+sway*q*q,HEIGHT+14.0-q*(176.0+b*38.0)))
            draw_polyline(poly,Color(.048,.083,.069,.38),7.0-b*.7,true)
            for leaf in range(4):
                var q: float = .27+float(leaf)*.17
                draw_circle(Vector2(base+dir*(39.0+b*20.0)*q+sway*q*q+dir*13.0,HEIGHT+14.0-q*(176.0+b*38.0)),4.0+float(leaf%2)*3.0,Color(.06,.12,.10,.34))
    # Localized fade in/out. Mid-film full frame is visible.
    var fade: float = maxf(1.0-smoothstep(0.0,1.0,t),smoothstep(12.75,14.0,t))
    draw_rect(Rect2(0.0,0.0,WIDTH,HEIGHT),Color(.012,.02,.034,fade))

func _draw() -> void:
    if texture == null or energy.size() != FRAMES:
        return
    var index: int = mini(frame_index,FRAMES-1)
    var t: float = float(index)/float(FPS)
    var e: float = float(energy[index])
    var b: float = float(onset[index])
    _background(t,e)
    _lighting(t,e,b)
    _haze(t,e)
    _air(t,e,b)
    _foreground(t,e)
