extends Node3D
# OpenGL-compatible, procedural 3D smoke. No imported production media.
var elapsed: float = 0.0
var subject: Node3D
var camera: Camera3D

func _material(color: Color, emission: float = 0.0) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    if emission > 0.0:
        material.emission_enabled = true
        material.emission = color
        material.emission_energy_multiplier = emission
    return material

func _box(parent: Node3D, size: Vector3, location: Vector3, color: Color) -> MeshInstance3D:
    var mesh_node := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = size
    mesh_node.mesh = mesh
    mesh_node.material_override = _material(color)
    mesh_node.position = location
    parent.add_child(mesh_node)
    return mesh_node

func _ready() -> void:
    var world := WorldEnvironment.new()
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color(0.045, 0.08, 0.15)
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color(0.3, 0.4, 0.55)
    environment.ambient_light_energy = 0.8
    world.environment = environment
    add_child(world)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48, 35, -15)
    sun.light_energy = 2.2
    add_child(sun)

    _box(self, Vector3(18.0, 0.18, 18.0), Vector3(0, -0.15, 0), Color(0.055, 0.15, 0.16))
    for i in range(9):
        var x: float = (float(i) - 4.0) * 1.65
        var height: float = 1.0 + float((i * 7) % 5) * 0.42
        _box(self, Vector3(0.65, height, 0.65), Vector3(x, height / 2.0, -2.0), Color(0.14 + 0.026 * float(i), 0.24, 0.34))
    subject = Node3D.new()
    add_child(subject)
    _box(subject, Vector3(1.6, 1.6, 1.6), Vector3(0.0, 1.18, 0.0), Color(0.93, 0.54, 0.27))
    _box(subject, Vector3(0.65, 2.9, 0.65), Vector3(0.0, 1.6, 0.0), Color(0.20, 0.80, 0.69))

    camera = Camera3D.new()
    camera.position = Vector3(1.0, 3.5, 8.0)
    add_child(camera)
    camera.current = true
    camera.look_at(Vector3(0.0, 1.0, -0.5))

func _process(delta: float) -> void:
    elapsed += delta
    subject.rotation.y = elapsed * 0.9
    camera.position = Vector3(sin(elapsed * 0.55) * 1.6, 3.1 + sin(elapsed * 0.3) * 0.3, 8.0)
    camera.look_at(Vector3(0.0, 1.0, -0.5))
