from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

# ==========================================
# Physics Constants (From your document)
# ==========================================
g = 9.81
k_drag = 0.12     # a_drag = -0.12 * v^2
k_lift = 0.0635   # Derived from Cl ~ 0.15

app = Ursina(title="3D First-Person Badminton", borderless=False, fullscreen=False)
window.color = color.rgb(20, 20, 40)  # Dark arena background

# ==========================================
# 3D Environment Setup
# ==========================================
# Court Floor
floor = Entity(model='plane', scale=(15, 1, 20), color=color.rgb(30, 100, 60), collider='box')

# Court Lines (White borders)
line_x = Entity(model='cube', scale=(13.4, 0.02, 0.1), position=(0, 0.01, 0), color=color.white)
line_z = Entity(model='cube', scale=(0.1, 0.02, 6.1), position=(0, 0.01, 0), color=color.white)
baseline_1 = Entity(model='cube', scale=(0.1, 0.02, 6.1), position=(-6.7, 0.01, 0), color=color.white)
baseline_2 = Entity(model='cube', scale=(0.1, 0.02, 6.1), position=(6.7, 0.01, 0), color=color.white)

# Visual 3D Net
net_mesh = Entity(model='plane', scale=(6.1, 1.55, 0.05), position=(0, 0.775, 0), 
                  color=color.rgba(255, 255, 255, 150))
# Used 'cube' instead of 'cylinder' for net posts to prevent missing model errors
net_post_1 = Entity(model='cube', scale=(0.08, 1.55, 0.08), position=(-3.1, 0.775, 0), color=color.rgb(100, 100, 100))
net_post_2 = Entity(model='cube', scale=(0.08, 1.55, 0.08), position=(3.1, 0.775, 0), color=color.rgb(100, 100, 100))
net_top = Entity(model='cube', scale=(6.1, 0.05, 0.06), position=(0, 1.55, 0), color=color.white)

# ==========================================
# Entities
# ==========================================
# Player (First Person Controller)
player = FirstPersonController(speed=8, jump_height=0)
player.position = (0, 1.7, -5.0)  # Start behind baseline
player.cursor.visible = False     # Hide default cursor for immersion

# Player Racket (attached to camera)
racket = Entity(parent=camera, model='cube', scale=(0.15, 0.15, 0.6), 
                position=(0.4, -0.3, 0.8), color=color.rgb(255, 50, 50), rotation=(0, 0, -15))
# Used 'cube' for racket handle
racket_handle = Entity(parent=racket, model='cube', scale=(0.05, 0.05, 0.4), 
                       position=(0, 0, -0.4), color=color.rgb(139, 69, 19))

# AI Opponent
ai = Entity(model='cube', scale=(0.6, 1.7, 0.6), position=(0, 0.85, 5.0), color=color.rgb(50, 100, 255))
ai_racket = Entity(parent=ai, model='cube', scale=(0.15, 0.15, 0.6), 
                   position=(0, 0.2, 0.4), color=color.rgb(255, 50, 50))

# Shuttlecock (Cork + Feathers)
shuttle = Entity(model='sphere', scale=0.08, color=color.white, position=(0, 1.5, -4.0))
# Used 'cube' instead of 'cone' for the skirt/feathers
feathers = Entity(parent=shuttle, model='cube', scale=(0.4, 0.4, 0.6), 
                  position=(0, 0, -0.3), color=color.rgb(240, 240, 240))

# Landing Prediction Circle
# Used 'circle' instead of 'ring'
predictor = Entity(model='circle', color=color.yellow, scale=1.0, rotation_x=90, visible=False)
predictor_text = Text(text="PREDICTED LANDING", origin=(0, 0), scale=1.5, color=color.yellow, visible=False, billboard=True)

# Trail
trail_entities = []

# ==========================================
# Game State
# ==========================================
score_player = 0
score_ai = 0
game_state = "ready"  # ready, playing, point_over
swing_timer = 0
ai_swing_timer = 0

score_text = Text(text=f"Player: {score_player}  |  AI: {score_ai}", position=(-0.85, 0.45), scale=2, color=color.white)
instr_text = Text(text="WASD to Move | Mouse to Look | LEFT CLICK to Hit/Serve", 
                  position=(0, -0.45), origin=(0, 0), scale=1.2, color=color.rgb(255, 255, 100))

# ==========================================
# Physics & Logic Functions
# ==========================================
def apply_physics(pos, vel, dt):
    """Applies the exact empirical physics from the document."""
    steps = 6  # Sub-stepping for high-speed stability
    sub_dt = dt / steps
    
    for _ in range(steps):
        speed = vel.length()
        if speed > 0.1:
            v_hat = vel.normalized()
            
            # 1. Drag: a = -0.12 * v^2
            a_drag = -k_drag * (speed ** 2) * v_hat
            
            # 2. Lift: Perpendicular to velocity, pointing "up" relative to flight path
            up = Vec3(0, 1, 0)
            lift_dir = up - (v_hat.dot(up) * v_hat)
            if lift_dir.length() > 0.001:
                a_lift = k_lift * (speed ** 2) * lift_dir.normalized()
            else:
                a_lift = Vec3(0, 0, 0)
                
            # 3. Gravity
            a_grav = Vec3(0, -g, 0)
            
            # Total acceleration
            a_total = a_drag + a_lift + a_grav
            
            # Update
            vel += a_total * sub_dt
            pos += vel * sub_dt
            
        # Floor Collision
        if pos.y <= 0.04:
            pos.y = 0.04
            vel = Vec3(0, 0, 0)
            return "floor"
            
        # Net Collision
        if abs(pos.z) < 0.15 and pos.y < 1.55:
            vel.z *= -0.4  # Bounce back weakly
            pos.z = 0.2 if pos.z < 0 else -0.2
            
    return "flying"

def get_predicted_landing(pos, vel):
    """Simulates the shuttle forward to find where it will land."""
    p = Vec3(pos)
    v = Vec3(vel)
    for _ in range(300):  # Max 300 simulation steps (~5 seconds of flight)
        speed = v.length()
        if speed > 0.1:
            v_hat = v.normalized()
            a_drag = -k_drag * (speed ** 2) * v_hat
            up = Vec3(0, 1, 0)
            lift_dir = up - (v_hat.dot(up) * v_hat)
            if lift_dir.length() > 0.001:
                a_lift = k_lift * (speed ** 2) * lift_dir.normalized()
            else:
                a_lift = Vec3(0, 0, 0)
            
            v += (a_drag + a_lift + Vec3(0, -g, 0)) * 0.016
            p += v * 0.016
            
            if p.y <= 0.04:
                return Vec3(p.x, 0.05, p.z)
    return None

def reset_point():
    global game_state
    game_state = "ready"
    shuttle.velocity = Vec3(0, 0, 0)
    shuttle.position = Vec3(0, 1.5, -4.0)
    predictor.visible = False
    predictor_text.visible = False
    
    # Clear trail
    for t in trail_entities:
        destroy(t)
    trail_entities.clear()

def update():
    global score_player, score_ai, game_state, swing_timer, ai_swing_timer
    
    dt = time.dt
    
    # --- Player Movement & Racket Swing ---
    if held_keys['left mouse'] and swing_timer <= 0:
        swing_timer = 0.3
        # Animate racket swing
        racket.animate_rotation((0, 0, -60), duration=0.1)
        racket.animate_position((0.4, -0.3, 1.2), duration=0.1)
        
        # Hit Detection
        dist = (shuttle.position - player.position).length()
        if dist < 1.8 and game_state == "playing":
            # Calculate hit direction (aim towards AI side with lift)
            target_x = random.uniform(-2.5, 2.5)
            target_z = 5.5
            hit_dir = Vec3(target_x - shuttle.position.x, 2.5 - shuttle.position.y, target_z - shuttle.position.z).normalized()
            
            # Smash or Clear based on timing
            speed = 35.0 + random.uniform(5, 15) 
            shuttle.velocity = hit_dir * speed
            
    # Return racket to idle
    if swing_timer > 0:
        swing_timer -= dt
        if swing_timer <= 0:
            racket.animate_rotation((0, 0, -15), duration=0.2)
            racket.animate_position((0.4, -0.3, 0.8), duration=0.2)

    # --- Serve Logic ---
    if game_state == "ready":
        if held_keys['left mouse'] and swing_timer <= 0:
            swing_timer = 0.3
            shuttle.velocity = Vec3(0, 12.0, 35.0)  # Up and forward serve
            game_state = "playing"

    # --- AI Logic ---
    if game_state == "playing":
        # AI moves to intercept shuttle X
        target_x = shuttle.position.x
        dx = target_x - ai.position.x
        ai.position.x += math.copysign(min(abs(dx), 6.0 * dt), dx)
        ai.position.x = max(-3.0, min(3.0, ai.position.x))  # Clamp to court
        
        # AI Height adjustment
        ai.position.y = 0.85 + max(0, (shuttle.position.y - 1.0) * 0.4)
        
        # AI Hit Detection
        ai_dist = (shuttle.position - ai.position).length()
        if ai_dist < 1.5 and shuttle.velocity.z > 0 and ai_swing_timer <= 0:
            ai_swing_timer = 0.4
            # AI returns the shuttle
            target_x = random.uniform(-2.5, 2.5)
            hit_dir = Vec3(target_x - shuttle.position.x, 2.0 - shuttle.position.y, -5.5 - shuttle.position.z).normalized()
            shuttle.velocity = hit_dir * 30.0

    if ai_swing_timer > 0:
        ai_swing_timer -= dt

    # --- Shuttle Physics & Orientation ---
    if game_state == "playing":
        status = apply_physics(shuttle.position, shuttle.velocity, dt)
        
        # Aerodynamic Passive Stability: Shuttle always flies cork-first!
        if shuttle.velocity.length() > 1.0:
            shuttle.look_at(shuttle.position + shuttle.velocity)
        
        # Trail rendering
        if len(trail_entities) < 100:
            t = Entity(model='sphere', scale=0.03, color=color.rgba(255, 100, 100, 150), position=Vec3(shuttle.position))
            trail_entities.append(t)
        elif trail_entities:
            trail_entities.pop(0).position = Vec3(shuttle.position)

        # Floor scoring
        if status == "floor":
            if shuttle.position.z > 0:
                score_player += 1
            else:
                score_ai += 1
            score_text.text = f"Player: {score_player}  |  AI: {score_ai}"
            game_state = "point_over"
            invoke(reset_point, delay=1.5)

    # --- Landing Prediction ---
    if game_state == "playing" and shuttle.velocity.length() > 1.0:
        pred = get_predicted_landing(shuttle.position, shuttle.velocity)
        if pred:
            predictor.position = pred
            predictor_text.position = (pred.x, pred.y + 0.5, pred.z)
            predictor.visible = True
            predictor_text.visible = True
        else:
            predictor.visible = False
            predictor_text.visible = False
    else:
        predictor.visible = False
        predictor_text.visible = False

    # Point over text
    if game_state == "point_over":
        instr_text.text = "Next point starting..."
    elif game_state == "ready":
        instr_text.text = "LEFT CLICK to Serve"
    else:
        instr_text.text = "Move with WASD | LEFT CLICK to Hit"

# Run the game
app.run()