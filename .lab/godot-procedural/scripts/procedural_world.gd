extends Node3D
# Authored 3D geometry from mathematical primitives. No image, texture, imported mesh,
# stock clip, image generator, or existing video in the rendering path.
const FRAME_COUNT: int = 336
const FPS: int = 24
var frame_index: int = 0
var energy: Array = []
var transients: Array = []
var camera: Camera3D
var halo_a: MeshInstance3D
var halo_b: MeshInstance3D
var heart: MeshInstance3D
var heart_light: OmniLight3D
var stars: MultiMeshInstance3D
var motes: MultiMeshInstance3D
var mist_nodes: Array[MeshInstance3D] = []

func material(c: Color, glow: float = 0.0, alpha: bool = false) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = 0.89
    m.metallic = 0.14
    if glow > 0.0:
        m.emission_enabled = true
        m.emission = Color(c.r, c.g, c.b)
        m.emission_energy_multiplier = glow
    if alpha:
        m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
        m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    return m

func spawn(mesh: Mesh, m: Material, p: Vector3, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.mesh = mesh
    node.material_override = m
    node.position = p
    node.rotation = rot
    add_child(node)
    return node

func block(size: Vector3, p: Vector3, m: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
    var mesh := BoxMesh.new()
    mesh.size = size
    return spawn(mesh, m, p, rot)

func pillar(radius: float, high: float, p: Vector3, m: Material, top_radius: float = -1.0) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.bottom_radius = radius
    mesh.top_radius = radius if top_radius < 0.0 else top_radius
    mesh.height = high
    mesh.radial_segments = 9
    return spawn(mesh, m, p)

func sphere(radius: float, p: Vector3, m: Material, scale3: Vector3 = Vector3.ONE) -> MeshInstance3D:
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = 2.0*radius
    mesh.radial_segments = 12
    mesh.rings = 6
    var n := spawn(mesh, m, p)
    n.scale = scale3
    return n

func terrain_height(x: float, z: float) -> float:
    var distance: float = Vector2(x,z).length()
    var spread: float = smoothstep(5.7,20.0,distance)
    return -0.52 + spread*(sin(x*0.21)*0.86+cos(z*0.18)*1.10+sin((x-z)*0.52)*0.42)

func build_ground() -> void:
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    const RES: int = 48
    const EXT: float = 43.0
    for zi in range(RES):
        for xi in range(RES):
            var xa: float = (float(xi)/RES-0.5)*2.0*EXT
            var xb: float = (float(xi+1)/RES-0.5)*2.0*EXT
            var za: float = (float(zi)/RES-0.5)*2.0*EXT
            var zb: float = (float(zi+1)/RES-0.5)*2.0*EXT
            var a := Vector3(xa,terrain_height(xa,za),za)
            var b := Vector3(xb,terrain_height(xb,za),za)
            var c := Vector3(xb,terrain_height(xb,zb),zb)
            var d := Vector3(xa,terrain_height(xa,zb),zb)
            for v in [a,c,b,a,d,c]:
                st.add_vertex(v)
    st.generate_normals()
    var land_mesh := st.commit()
    spawn(land_mesh,material(Color(0.10,0.145,0.166)),Vector3.ZERO)
    # Geological relief boulders, all constructed from vertices and primitive meshes.
    var stone := material(Color(0.155,0.20,0.23))
    for i in range(90):
        var k: float = float(i)
        var theta: float = k*2.3999632297
        var radius: float = 7.0+fposmod(k*7.73,22.0)
        var x: float = sin(theta)*radius
        var z: float = cos(theta)*radius
        var w: float = 0.55+fposmod(k*.67,1.8)
        var tall: float = 0.5+fposmod(k*.371,2.2)
        block(Vector3(w,tall,w*.85),Vector3(x,terrain_height(x,z)+tall*.4,z),stone,Vector3(k*.07,k*.71,k*.11))

func build_ruins() -> void:
    var granite := material(Color(0.235,0.258,0.29))
    var dark := material(Color(0.102,0.14,0.17))
    var brass := material(Color(0.33,0.24,0.155))
    var moon := material(Color(0.14,0.77,0.86),2.7)
    var amber := material(Color(0.98,0.49,0.15),2.8)
    pillar(5.8,0.75,Vector3(0,-0.20,0),granite)
    pillar(4.7,0.28,Vector3(0,0.31,0),brass)
    pillar(3.7,0.22,Vector3(0,0.49,0),dark)
    # Real depth: twelve freestanding broken pillars and overhead lintels.
    for i in range(12):
        var theta: float = float(i)*TAU/12.0
        var rad: float = 8.1
        var x: float = cos(theta)*rad
        var z: float = sin(theta)*rad
        var high: float = 2.1+float((i*7)%6)*0.61
        pillar(.44,high,Vector3(x,terrain_height(x,z)+high*.5,z),granite)
        pillar(.62,.22,Vector3(x,terrain_height(x,z)+high+.08,z),brass)
        if i%3 != 1:
            var next_theta: float = theta+TAU/12.0
            var xx: float = cos(next_theta)*rad
            var zz: float = sin(next_theta)*rad
            var p := Vector3((x+xx)*.5,terrain_height(x,z)+high+.2,(z+zz)*.5)
            block(Vector3(3.7,.34,.46),p,granite,Vector3(0,-theta+PI*.5,0))
    for i in range(7):
        var theta: float = (float(i)+.35)*TAU/7.0
        var pos := Vector3(cos(theta)*3.1,.67,sin(theta)*3.1)
        pillar(.68,1.7,pos+Vector3(0,.45,0),dark,.05)
        sphere(.28,pos+Vector3(0,1.42,0),amber)
    # Original new 3D monolith core, separated in depth from surrounding ruins.
    pillar(1.9,1.02,Vector3(0,.9,0),dark)
    pillar(1.25,1.55,Vector3(0,1.98,0),brass,.48)
    heart = sphere(.83,Vector3(0,3.15,0),moon,Vector3(1.0,1.35,1.0))
    var tor := TorusMesh.new()
    tor.inner_radius = 1.55
    tor.outer_radius = 1.62
    tor.rings = 24
    tor.ring_segments = 9
    halo_a = spawn(tor,moon,Vector3(0,3.1,0),Vector3(.35,0,.6))
    halo_b = spawn(tor,amber,Vector3(0,3.1,0),Vector3(1.1,0,.2))
    for i in range(18):
        var k: float = float(i)
        var theta: float = k*TAU/18.0
        var r: float = 10.5+fposmod(k*1.9,6.0)
        pillar(.30,1.0+fposmod(k*.53,2.8),Vector3(cos(theta)*r,.3+fposmod(k*.53,2.8)*.5,sin(theta)*r),granite,.06)
    # Raised approach toward center, reads in the camera foreground.
    for i in range(12):
        var z: float = 6.5+float(i)*1.75
        block(Vector3(2.4,.20,1.35),Vector3(0,terrain_height(0,z)+.14,z),granite,Vector3(0,sin(float(i)*.7)*.085,0))

func build_air() -> void:
    var mist_mat := material(Color(.48,.69,.74,.06),0.0,true)
    for i in range(24):
        var theta: float = float(i)*2.39996
        var rad: float = 3.0+fposmod(float(i)*2.42,20.0)
        var node := sphere(1.2,Vector3(cos(theta)*rad,.03,sin(theta)*rad),mist_mat,Vector3(2.8,0.19,1.7))
        mist_nodes.append(node)
    var stars_mat := material(Color(.64,.86,1.0),1.8)
    var star_mesh := SphereMesh.new()
    star_mesh.radius = .11
    star_mesh.height = .22
    star_mesh.radial_segments = 6
    star_mesh.rings = 3
    var mm := MultiMesh.new()
    mm.transform_format = MultiMesh.TRANSFORM_3D
    mm.instance_count = 110
    mm.mesh = star_mesh
    for i in range(110):
        var k: float = float(i)
        var angle: float = k*2.399963
        var r: float = 62.0+fposmod(k*8.1,22.0)
        var yy: float = 22.0+fposmod(k*7.13,44.0)
        mm.set_instance_transform(i,Transform3D(Basis().scaled(Vector3.ONE*(0.5+fposmod(k*.81,1.1))),Vector3(r*sin(angle),yy,r*cos(angle))))
    stars = MultiMeshInstance3D.new()
    stars.multimesh = mm
    stars.material_override = stars_mat
    add_child(stars)
    var mote_mesh := SphereMesh.new()
    mote_mesh.radius = .043
    mote_mesh.height = .086
    mote_mesh.radial_segments = 6
    mote_mesh.rings = 3
    var embers := MultiMesh.new()
    embers.transform_format = MultiMesh.TRANSFORM_3D
    embers.instance_count = 80
    embers.mesh = mote_mesh
    motes = MultiMeshInstance3D.new()
    motes.multimesh = embers
    motes.material_override = material(Color(.96,.59,.22),3.0)
    add_child(motes)

func _ready() -> void:
    var f := FileAccess.open("res://data/audio_drive.json",FileAccess.READ)
    if f == null:
        push_error("Verified WAV analysis is mandatory.")
        get_tree().quit(1)
        return
    var obj: Variant = JSON.parse_string(f.get_as_text())
    if typeof(obj) != TYPE_DICTIONARY:
        push_error("Unparseable music controls")
        get_tree().quit(1)
        return
    energy = obj.get("energy",[])
    transients = obj.get("onset",[])
    if energy.size()!=FRAME_COUNT or transients.size()!=FRAME_COUNT:
        push_error("Wrong music control length, expected 336 measured frames")
        get_tree().quit(1)
        return
    var world := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color(.011,.021,.042)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color(.19,.31,.45)
    env.ambient_light_energy = .61
    env.fog_enabled = true
    env.fog_light_color = Color(.12,.24,.28)
    env.fog_density = .011
    world.environment = env
    add_child(world)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-42,32,0)
    sun.light_color = Color(.42,.63,.81)
    sun.light_energy = .74
    add_child(sun)
    build_ground()
    build_ruins()
    build_air()
    heart_light = OmniLight3D.new()
    heart_light.position = Vector3(0,3.5,0)
    heart_light.light_color = Color(.15,.76,1.0)
    heart_light.omni_range = 19.0
    heart_light.light_energy = 2.2
    add_child(heart_light)
    var accent := OmniLight3D.new()
    accent.position = Vector3(3,3,3)
    accent.light_color = Color(1.0,.47,.16)
    accent.omni_range = 12.0
    accent.light_energy = 1.3
    add_child(accent)
    camera = Camera3D.new()
    camera.fov = 58.0
    camera.near = .07
    camera.far = 150.0
    add_child(camera)
    camera.current = true

func _process(_delta: float) -> void:
    var i: int = mini(frame_index,FRAME_COUNT-1)
    var t: float = float(i)/FPS
    var e: float = float(energy[i])
    var beat: float = float(transients[i])
    # Physical 3D dolly/orbit, all pillars and mountain ridges exhibit real parallax.
    var a: float = .33 + t*.104
    var radius: float = lerpf(21.0,11.8,smoothstep(0.0,13.9,t))
    camera.position = Vector3(sin(a)*radius,4.4+sin(t*.26)*.72+beat*.14,cos(a)*radius)
    camera.look_at(Vector3(0,2.1+e*.18,0),Vector3.UP)
    heart.position.y = 3.15+sin(t*1.2)*.17+e*.09
    halo_a.rotation.y = t*.58
    halo_a.rotation.z = .4+sin(t*.53)*.4
    halo_b.rotation.x = t*.74
    halo_b.rotation.y = t*.44
    var pulse: float = 1.0+.26*e+.32*beat
    halo_a.scale = Vector3.ONE*pulse
    halo_b.scale = Vector3.ONE*(1.08+.11*e)
    heart_light.light_energy = 1.4+3.0*e+2.2*beat
    for j in range(mist_nodes.size()):
        var n: MeshInstance3D = mist_nodes[j]
        n.position.x += sin(t*.37+float(j)*.81)*.007
        n.position.z += cos(t*.31+float(j)*.41)*.006
    for j in range(80):
        var k: float = float(j)
        var theta: float = k*2.399963 + t*(.16+float(j%7)*.011)
        var r: float = 1.35+fposmod(k*1.93,11.0)
        var h: float = .15+fposmod(k*.73+t*(.27+.24*e),6.0)
        var pos := Vector3(sin(theta)*r,h,cos(theta)*r)
        var ss: float = .65+.33*e+.35*beat
        motes.multimesh.set_instance_transform(j,Transform3D(Basis().scaled(Vector3.ONE*ss),pos))
    frame_index+=1
