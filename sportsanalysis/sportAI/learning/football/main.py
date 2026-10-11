#!/usr/bin/env python3
"""
=======================================================================
  3D SOCCER FREE KICK AI  —  ULTRA-FAST TOP CORNER OPTIMISATION
=======================================================================
  * Full 3D physics (gravity, aerodynamic drag, Magnus effect for curve/dip).
  * Defensive wall collision logic (9.15m / 10 yards from ball).
  * PHYSICS PRE-TRAINING: Instantly learns ~1000 physics-derived shots 
    before the first frame, giving it immediate "free kick intuition".
  * DIRECTED EXPLORATION: Explores by adding noise to its best guess.
  * Adaptive hill-climbing to "perfect" the shot combination.
  * Brain saves every 100 shots to freekick_brain.pkl

  Controls
  --------
    SPACE   pause/resume
    T       turbo (20 shots/frame)
    A       cycle mode:  AUTO -> FIXED -> OPTIMAL
    C       wipe brain
    1-5     animation speed
    click   adjust horizontal aim bias
    ESC     quit
=======================================================================
"""

import os
import math
import pickle
from collections import deque

import numpy as np
import pygame

# =====================================================================
#  PHYSICS CONSTANTS
# =====================================================================
G                  = 9.81
BALL_R             = 0.11    # Soccer ball radius (m)
BALL_MASS          = 0.43    # Soccer ball mass (kg)
DRAG_COEFF         = 0.0025  # Aerodynamic drag factor
MAGNUS_K           = 0.0008  # Magnus effect coefficient (curve/dip)

GOAL_WIDTH         = 7.32    # 8 yards
GOAL_HEIGHT        = 2.44    # 8 feet
GOAL_Z             = 0.0     # Goal line

# Ball starts 25 yards (22.86m) away, offset to the left (for a right-footed curl)
BALL_START_X       = -10.0   
BALL_START_Z       = 22.86
BALL_START_Y       = BALL_R

# Defensive wall: 10 yards (9.15m) from the ball
WALL_Z             = BALL_START_Z - 9.15
WALL_X_MIN         = -12.0   # Wall blocks the near post angle
WALL_X_MAX         = -2.0
WALL_HEIGHT        = 1.8     # Average jumping height

DT                 = 0.002
MAX_T              = 4.0     # Max flight time (seconds)

# Action space
H_ANGLE_MIN, H_ANGLE_MAX = -15.0, 15.0   # Horizontal aim (degrees, 0 = straight at goal center)
V_ANGLE_MIN, V_ANGLE_MAX = 5.0, 25.0     # Vertical elevation (degrees)
SPEED_MIN, SPEED_MAX     = 18.0, 35.0    # Kick speed (m/s)
SPIN_MIN, SPIN_MAX       = -15.0, 15.0   # Side spin (rad/s, positive = curves right/inward)

def norm_ha(a): return (a - 0.0) / 15.0
def norm_va(a): return (a - 15.0) / 10.0
def norm_sp(s): return (s - 26.5) / 8.5
def norm_si(s): return s / 15.0

def den_ha(x): return x * 15.0
def den_va(x): return x * 10.0 + 15.0
def den_sp(x): return x * 8.5 + 26.5
def den_si(x): return x * 15.0


# =====================================================================
#  BALL PHYSICS
# =====================================================================
def simulate(h_angle_deg, v_angle_deg, speed, side_spin):
    """
    Simulate soccer ball with Drag and Magnus effect.
    Returns: trajectory, goal (bool), hit_wall (bool), hit_post (bool)
    """
    h_rad = math.radians(h_angle_deg)
    v_rad = math.radians(v_angle_deg)
    
    x = BALL_START_X
    y = BALL_START_Y
    z = BALL_START_Z
    
    # Initial velocity vector (kicking towards Z=0)
    vx = speed * math.sin(h_rad) * math.cos(v_rad)
    vy = speed * math.sin(v_rad)
    vz = -speed * math.cos(h_rad) * math.cos(v_rad)
    
    # Spin vector: side_spin is around Y axis. We add a little top-spin automatically for dip.
    omega_x = -5.0  # Fixed slight top-spin for dip
    omega_y = side_spin
    omega_z = 0.0
    
    positions = [(x, y, z)]
    t = 0.0
    
    goal = False
    hit_wall = False
    hit_post = False
    
    while t < MAX_T:
        px, py, pz = x, y, z
        
        # Velocity magnitude
        v_mag = math.sqrt(vx*vx + vy*vy + vz*vz)
        if v_mag < 0.5:
            break
            
        # 1. Gravity
        ax, ay, az = 0.0, -G, 0.0
        
        # 2. Aerodynamic Drag (opposes velocity)
        drag_f = DRAG_COEFF * v_mag
        ax -= drag_f * vx
        ay -= drag_f * vy
        az -= drag_f * vz
        
        # 3. Magnus Effect: F = K * (omega x v)
        # Cross product: omega x v
        mx = omega_y * vz - omega_z * vy
        my = omega_z * vx - omega_x * vz
        mz = omega_x * vy - omega_y * vx
        
        ax += MAGNUS_K * mx
        ay += MAGNUS_K * my
        az += MAGNUS_K * mz
        
        # Symplectic Euler integration
        vx += ax * DT
        vy += ay * DT
        vz += az * DT
        
        x += vx * DT
        y += vy * DT
        z += vz * DT
        t += DT
        
        # Wall Collision
        if pz > WALL_Z >= z and not hit_wall:
            if WALL_X_MIN <= x <= WALL_X_MAX and 0 <= y <= WALL_HEIGHT:
                hit_wall = True
                vz = -vz * 0.3  # Bounce back weakly
                vx = vx * 0.5
                vy = vy * 0.5
        
        # Goal Plane Crossing
        if pz > GOAL_Z >= z and not goal and not hit_wall:
            # Check if inside goal frame
            if -GOAL_WIDTH/2 <= x <= GOAL_WIDTH/2 and 0 <= y <= GOAL_HEIGHT:
                goal = True
                break
            # Check for post hit
            elif abs(abs(x) - GOAL_WIDTH/2) < BALL_R and 0 <= y <= GOAL_HEIGHT:
                hit_post = True
                vx = -vx * 0.5
                vz = -vz * 0.5
            # Check for crossbar hit
            elif -GOAL_WIDTH/2 <= x <= GOAL_WIDTH/2 and abs(y - GOAL_HEIGHT) < BALL_R:
                hit_post = True
                vy = -vy * 0.5
                vz = -vz * 0.5
                
        # Ground hit
        if y <= BALL_R:
            y = BALL_R
            vy = -vy * 0.6  # Bounce
            vx *= 0.7       # Friction
            vz *= 0.7
            if v_mag < 2.0:
                break
                
        positions.append((x, y, z))
        
        # Out of bounds safety
        if z < -5.0 or abs(x) > 25.0 or y > 15.0:
            break

    return positions, goal, hit_wall, hit_post


# =====================================================================
#  NEURAL NET
# =====================================================================
class Net:
    def __init__(self, n_in=4, h=64, seed=1, lr=2.5e-3):
        rng = np.random.default_rng(seed)
        def mk(a, b):
            return rng.standard_normal((a, b)) * math.sqrt(2.0 / a)
        self.W1, self.b1 = mk(n_in, h), np.zeros(h)
        self.W2, self.b2 = mk(h, h),    np.zeros(h)
        self.W3, self.b3 = mk(h, 1),    np.zeros(1)
        self.params = [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t = 0
        self.lr = lr

    def forward(self, X, cache=False):
        z1 = X @ self.W1 + self.b1; h1 = np.tanh(z1)
        z2 = h1 @ self.W2 + self.b2; h2 = np.tanh(z2)
        out = h2 @ self.W3 + self.b3
        if cache: return out, (X, h1, h2)
        return out

    def backward(self, cache, dout):
        X, h1, h2 = cache
        dW3 = h2.T @ dout; db3 = dout.sum(0)
        dh2 = dout @ self.W3.T; dz2 = dh2 * (1.0 - h2*h2)
        dW2 = h1.T @ dz2; db2 = dz2.sum(0)
        dh1 = dz2 @ self.W2.T; dz1 = dh1 * (1.0 - h1*h1)
        dW1 = X.T @ dz1; db1 = dz1.sum(0)
        dX  = dz1 @ self.W1.T
        return [dW1, db1, dW2, db2, dW3, db3], dX

    def step(self, grads):
        self.t += 1
        b1, b2, eps = 0.9, 0.999, 1e-8
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.m[i] = b1*self.m[i] + (1-b1)*g
            self.v[i] = b2*self.v[i] + (1-b2)*g*g
            mh = self.m[i] / (1 - b1**self.t)
            vh = self.v[i] / (1 - b2**self.t)
            p -= self.lr * mh / (np.sqrt(vh) + eps)

    def train_batch(self, X, Y):
        out, cache = self.forward(X, cache=True)
        dout = 2.0 * (out - Y) / X.shape[0]
        grads, _ = self.backward(cache, dout)
        self.step(grads)


# =====================================================================
#  ACTION SELECTION & OPTIMIZATION
# =====================================================================

def evaluate_shot(net, ha, va, sp, si):
    X = np.array([[norm_ha(ha), norm_va(va), norm_sp(sp), norm_si(si)]], dtype=np.float64)
    pred = float(net.forward(X)[0, 0])
    return pred  # Expected goal probability (0.0 to 1.0)


def refine_free_kick(net, start_ha, start_va, start_sp, start_si, max_iters=80):
    c_ha, c_va, c_sp, c_si = start_ha, start_va, start_sp, start_si
    c_val = evaluate_shot(net, c_ha, c_va, c_sp, c_si)
    
    steps = [2.0, 2.0, 2.0, 2.0]
    min_steps = [0.1, 0.1, 0.2, 0.2]
    
    for _ in range(max_iters):
        best_ha, best_va, best_sp, best_si, best_val = c_ha, c_va, c_sp, c_si, c_val
        
        # Generate neighbors
        for i in range(4):
            for sign in [-1, 1]:
                n_ha, n_va, n_sp, n_si = c_ha, c_va, c_sp, c_si
                if i == 0: n_ha = np.clip(c_ha + sign * steps[0], H_ANGLE_MIN, H_ANGLE_MAX)
                elif i == 1: n_va = np.clip(c_va + sign * steps[1], V_ANGLE_MIN, V_ANGLE_MAX)
                elif i == 2: n_sp = np.clip(c_sp + sign * steps[2], SPEED_MIN, SPEED_MAX)
                elif i == 3: n_si = np.clip(c_si + sign * steps[3], SPIN_MIN, SPIN_MAX)
                
                val = evaluate_shot(net, n_ha, n_va, n_sp, n_si)
                if val > best_val:
                    best_val = val
                    best_ha, best_va, best_sp, best_si = n_ha, n_va, n_sp, n_si
        
        if best_val > c_val:
            c_ha, c_va, c_sp, c_si, c_val = best_ha, best_va, best_sp, best_si, best_val
        else:
            steps = [s * 0.5 for s in steps]
            
        if all(s < m for s, m in zip(steps, min_steps)):
            break
            
    return c_ha, c_va, c_sp, c_si, c_val


def best_action(net, n_samples=500):
    # Random sampling for 4D space (much faster than dense meshgrid)
    rng = np.random.default_rng(42)
    has = rng.uniform(H_ANGLE_MIN, H_ANGLE_MAX, n_samples)
    vas = rng.uniform(V_ANGLE_MIN, V_ANGLE_MAX, n_samples)
    sps = rng.uniform(SPEED_MIN, SPEED_MAX, n_samples)
    sis = rng.uniform(SPIN_MIN, SPIN_MAX, n_samples)
    
    Xc = np.column_stack([norm_ha(has), norm_va(vas), norm_sp(sps), norm_si(sis)])
    preds = net.forward(Xc).ravel()
    
    # Take top 5 and refine
    order = np.argsort(preds)[-5:]
    
    best_overall = None
    for i in order:
        ha, va, sp, si, val = refine_free_kick(net, has[i], vas[i], sps[i], sis[i])
        if best_overall is None or val > best_overall[4]:
            best_overall = (ha, va, sp, si, val)
            
    return best_overall


# =====================================================================
#  GLOBAL STATE & PRE-TRAINING
# =====================================================================
BUFSIZE = 40000
net     = Net()
buf_X   = np.zeros((BUFSIZE, 4))
buf_Y   = np.zeros((BUFSIZE, 1))
buf_n   = 0
buf_ptr = 0
rng     = np.random.default_rng(12345)

shots   = 0
goals   = 0
hit_wall_count = 0
hit_post_count = 0

SAVE_PATH = os.path.join(os.getcwd(), "freekick_brain.pkl")

def epsilon(): return max(0.05, 0.80 * math.exp(-shots / 250.0))


def add_sample(ha, va, sp, si, outcome):
    global buf_n, buf_ptr
    buf_X[buf_ptr, 0] = norm_ha(ha)
    buf_X[buf_ptr, 1] = norm_va(va)
    buf_X[buf_ptr, 2] = norm_sp(sp)
    buf_X[buf_ptr, 3] = norm_si(si)
    buf_Y[buf_ptr, 0] = outcome  # 1.0 for goal, 0.5 for post, 0.0 for miss/wall
    buf_ptr = (buf_ptr + 1) % BUFSIZE
    if buf_n < BUFSIZE: buf_n += 1


def train_steps(k=2, batch=128):
    if buf_n < 64: return
    for _ in range(k):
        idx = rng.integers(0, buf_n, size=min(batch, buf_n))
        net.train_batch(buf_X[idx], buf_Y[idx])


def choose_action(greedy=False):
    best_ha, best_va, best_sp, best_si, _ = best_action(net)
    
    if not greedy and (shots < 120 or rng.random() < epsilon()):
        noise = epsilon()
        ha = best_ha + rng.normal(0.0, 3.0 * noise)
        va = best_va + rng.normal(0.0, 2.0 * noise)
        sp = best_sp + rng.normal(0.0, 2.0 * noise)
        si = best_si + rng.normal(0.0, 3.0 * noise)
    else:
        ha, va, sp, si = best_ha, best_va, best_sp, best_si
    
    return (float(np.clip(ha, H_ANGLE_MIN, H_ANGLE_MAX)),
            float(np.clip(va, V_ANGLE_MIN, V_ANGLE_MAX)),
            float(np.clip(sp, SPEED_MIN, SPEED_MAX)),
            float(np.clip(si, SPIN_MIN, SPIN_MAX)))


def pretrain_brain():
    print("Pre-training brain with free kick physics priors...")
    for _ in range(1500):
        # Bias pre-training towards realistic free kicks:
        # Aim slightly wide (positive h_angle) and curve it in (positive side_spin)
        # OR aim straight and dip it (high v_angle, negative side_spin or top spin)
        if rng.random() < 0.7:
            # Curling shot around the wall
            ha = rng.uniform(2.0, 10.0)
            si = rng.uniform(5.0, 14.0)
            va = rng.uniform(8.0, 18.0)
            sp = rng.uniform(22.0, 30.0)
        else:
            # Power shot / dipper
            ha = rng.uniform(-5.0, 5.0)
            si = rng.uniform(-5.0, 5.0)
            va = rng.uniform(12.0, 22.0)
            sp = rng.uniform(26.0, 34.0)
            
        _, goal, wall, post = simulate(ha, va, sp, si)
        outcome = 1.0 if goal else (0.5 if post else 0.0)
        add_sample(ha, va, sp, si, outcome)
    
    for _ in range(80):
        train_steps(k=5, batch=256)
    print("Pre-training complete. AI has free kick intuition!")


# =====================================================================
#  SAVE / LOAD
# =====================================================================
def save_brain():
    data = {
        "params": [p.copy() for p in net.params], "adam_m": [m.copy() for m in net.m],
        "adam_v": [v.copy() for v in net.v], "adam_t": net.t,
        "buf_X": buf_X, "buf_Y": buf_Y, "buf_n": buf_n, "buf_ptr": buf_ptr,
        "shots": shots, "goals": goals, "hit_wall_count": hit_wall_count, "hit_post_count": hit_post_count,
    }
    tmp = SAVE_PATH + ".tmp"
    try:
        with open(tmp, "wb") as f:
            pickle.dump(data, f, protocol=4)
        os.replace(tmp, SAVE_PATH)
        return True
    except Exception as e:
        print("save failed:", e); return False


def load_brain():
    global buf_X, buf_Y, buf_n, buf_ptr, shots, goals, hit_wall_count, hit_post_count
    if not os.path.exists(SAVE_PATH): return False
    try:
        with open(SAVE_PATH, "rb") as f:
            data = pickle.load(f)
        for p, v in zip(net.params, data["params"]): p[...] = v
        for m, v in zip(net.m, data["adam_m"]): m[...] = v
        for m, v in zip(net.v, data["adam_v"]): m[...] = v
        net.t = data["adam_t"]
        buf_X, buf_Y = data["buf_X"], data["buf_Y"]
        buf_n, buf_ptr = data["buf_n"], data["buf_ptr"]
        shots = data["shots"]
        goals = data["goals"]
        hit_wall_count = data.get("hit_wall_count", 0)
        hit_post_count = data.get("hit_post_count", 0)
        return True
    except Exception as e:
        print("load failed:", e); return False


def wipe_brain():
    global net, buf_X, buf_Y, buf_n, buf_ptr, shots, goals, hit_wall_count, hit_post_count
    net = Net()
    buf_X = np.zeros((BUFSIZE, 4)); buf_Y = np.zeros((BUFSIZE, 1))
    buf_n = buf_ptr = 0
    shots = goals = hit_wall_count = hit_post_count = 0
    if os.path.exists(SAVE_PATH):
        try: os.remove(SAVE_PATH)
        except OSError: pass
    pretrain_brain()


# =====================================================================
#  3D RENDERING
# =====================================================================
W, H = 1280, 720

class Camera:
    def __init__(self, pos, target, fov=60):
        self.pos = np.array(pos, dtype=float)
        f = np.array(target, dtype=float) - self.pos
        f = f / np.linalg.norm(f)
        up = np.array([0.0, 1.0, 0.0])
        r = np.cross(f, up); r = r / np.linalg.norm(r)
        u = np.cross(r, f)
        self.forward, self.right, self.up = f, r, u
        self.f = 0.5 * H / math.tan(math.radians(fov) / 2)

    def project(self, pt):
        p = np.array(pt, dtype=float) - self.pos
        x = p.dot(self.right); y = p.dot(self.up); z = p.dot(self.forward)
        if z < 0.08: return None
        return (W/2 + self.f * x / z, H/2 - self.f * y / z, z)

    def radius(self, pt, r):
        p = np.array(pt, dtype=float) - self.pos
        z = p.dot(self.forward)
        if z < 0.08: return None
        return self.f * r / z

def line3(screen, cam, p1, p2, color, width=2):
    a = cam.project(p1); b = cam.project(p2)
    if a and b:
        pygame.draw.line(screen, color, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), width)

def poly3(screen, cam, pts, fill=None, outline=None, width=2):
    ps = [cam.project(p) for p in pts]
    if any(p is None for p in ps): return
    pxy = [(int(p[0]), int(p[1])) for p in ps]
    if fill is not None: pygame.draw.polygon(screen, fill, pxy)
    if outline is not None: pygame.draw.polygon(screen, outline, pxy, width)

def draw_pitch(screen, cam):
    # Grass
    poly3(screen, cam, [(-20, 0, 30), (20, 0, 30), (20, 0, -10), (-20, 0, -10)],
          fill=(34, 139, 34), outline=(20, 100, 20), width=2)
    
    # Penalty box lines (simplified)
    line3(screen, cam, (-20, 0.01, 0), (20, 0.01, 0), (255, 255, 255), 2)
    line3(screen, cam, (-8, 0.01, 0), (-8, 0.01, 16.5), (255, 255, 255), 2)
    line3(screen, cam, (8, 0.01, 0), (8, 0.01, 16.5), (255, 255, 255), 2)
    line3(screen, cam, (-8, 0.01, 16.5), (8, 0.01, 16.5), (255, 255, 255), 2)

def draw_goal(screen, cam):
    hw = GOAL_WIDTH / 2
    hh = GOAL_HEIGHT
    # Posts
    line3(screen, cam, (-hw, 0, GOAL_Z), (-hw, hh, GOAL_Z), (255, 255, 255), 4)
    line3(screen, cam, (hw, 0, GOAL_Z), (hw, hh, GOAL_Z), (255, 255, 255), 4)
    # Crossbar
    line3(screen, cam, (-hw, hh, GOAL_Z), (hw, hh, GOAL_Z), (255, 255, 255), 4)
    # Net (simplified grid)
    for i in range(5):
        z_net = GOAL_Z - i * 0.4
        line3(screen, cam, (-hw, 0, z_net), (-hw, hh, z_net), (200, 200, 200), 1)
        line3(screen, cam, (hw, 0, z_net), (hw, hh, z_net), (200, 200, 200), 1)
        line3(screen, cam, (-hw, hh, z_net), (hw, hh, z_net), (200, 200, 200), 1)

def draw_wall(screen, cam):
    # Draw 4 defenders as simple cylinders/boxes
    for i in range(4):
        wx = WALL_X_MIN + i * 1.5
        wy = 0.9
        wz = WALL_Z
        # Body
        line3(screen, cam, (wx, 0, wz), (wx, 1.8, wz), (220, 50, 50), 8)
        # Head
        pr = cam.project((wx, 1.9, wz))
        if pr:
            rad = max(3, int(cam.radius((wx, 1.9, wz), 0.15) or 3))
            pygame.draw.circle(screen, (255, 220, 180), (int(pr[0]), int(pr[1])), rad)

def draw_ball(screen, cam, pos, color=(255, 255, 255)):
    pr = cam.project(pos)
    if pr is None: return
    rad = cam.radius(pos, BALL_R)
    if rad is None or rad < 1: return
    pygame.draw.circle(screen, color, (int(pr[0]), int(pr[1])), int(rad))
    pygame.draw.circle(screen, (0, 0, 0), (int(pr[0]), int(pr[1])), max(1, int(rad)), 1)

def draw_trail(screen, cam, pts, idx, color):
    n = max(2, int(idx))
    prev = None
    for i in range(min(n, len(pts))):
        pr = cam.project(pts[i])
        if pr is None: prev = None; continue
        if prev is not None: 
            pygame.draw.line(screen, color, prev, (int(pr[0]), int(pr[1])), 2)
        prev = (int(pr[0]), int(pr[1]))

def draw_kicker(screen, cam, pos_x, pos_z):
    # Simplified kicker figure behind the ball
    base = (pos_x - 0.5, 0, pos_z + 0.5)
    torso = (pos_x - 0.5, 1.4, pos_z + 0.5)
    line3(screen, cam, base, (pos_x - 0.6, 0.8, pos_z + 0.5), (30, 60, 150), 6)
    line3(screen, cam, base, (pos_x - 0.4, 0.8, pos_z + 0.5), (30, 60, 150), 6)
    line3(screen, cam, (pos_x - 0.5, 0.8, pos_z + 0.5), torso, (30, 60, 150), 8)
    pr = cam.project(torso)
    if pr:
        rad = max(5, int(cam.radius(torso, 0.12) or 5))
        pygame.draw.circle(screen, (255, 220, 180), (int(pr[0]), int(pr[1])), rad)


# =====================================================================
#  MAIN
# =====================================================================
def main():
    global shots, goals, hit_wall_count, hit_post_count

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("3D Soccer Free Kick AI — TOP CORNER OPTIMISATION")
    clock = pygame.time.Clock()

    try:
        f_big = pygame.font.SysFont("consolas,couriernew,monospace", 22, bold=True)
        f     = pygame.font.SysFont("consolas,couriernew,monospace", 18, bold=True)
        f_s   = pygame.font.SysFont("consolas,couriernew,monospace", 14)
    except Exception:
        f_big = pygame.font.Font(None, 26)
        f     = pygame.font.Font(None, 22)
        f_s   = pygame.font.Font(None, 16)

    # Camera positioned behind and slightly to the side of the kicker
    cam = Camera((BALL_START_X - 2.0, 4.0, BALL_START_Z + 6.0), (0.0, 1.5, 0.0), fov=65)

    if os.path.exists(SAVE_PATH):
        try:
            os.remove(SAVE_PATH)
            print("Deleted old brain file to start fresh.")
        except OSError:
            pass

    loaded = load_brain()
    if not loaded:
        pretrain_brain()
    else:
        print("loaded existing brain")

    state, cur_pts, cur_idx = "ready", [], 0.0
    cur_goal, cur_wall, cur_post = False, False, False
    cur_action = (0.0, 15.0, 25.0, 0.0)
    turbo, paused, speed_mult, mode = False, False, 1.0, 0
    recent, TURBO_N = deque(maxlen=100), 20

    def do_kick(ha=None, va=None, sp=None, si=None, greedy=False):
        nonlocal cur_goal, cur_wall, cur_post
        global shots, goals, hit_wall_count, hit_post_count

        if ha is None:
            if mode == 2:  # OPTIMAL
                best_ha, best_va, best_sp, best_si, _ = best_action(net)
                ha, va, sp, si = best_ha, best_va, best_sp, best_si
                greedy = True
            else:
                ha, va, sp, si = choose_action(greedy=greedy)

        trajectory, goal, wall, post = simulate(ha, va, sp, si)
        
        outcome = 1.0 if goal else (0.5 if post else 0.0)
        add_sample(ha, va, sp, si, outcome)

        k = 5 if shots < 500 else 2
        batch = 256 if shots < 500 else 128
        train_steps(k=k, batch=batch)

        shots += 1
        if goal: goals += 1
        if wall: hit_wall_count += 1
        if post: hit_post_count += 1
        
        cur_goal, cur_wall, cur_post = goal, wall, post
        recent.append(1 if goal else 0)

        if shots % 100 == 0:
            save_brain()
            print(f"  [{shots:5d} shots | {goals} goals | "
                  f"{100.0*goals/shots:5.1f}% conversion] saved")

        return ha, va, sp, si, trajectory, goal, wall, post

    running = True
    while running:
        dt_real = min(clock.tick(60) / 1000.0, 0.05)

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_SPACE: paused = not paused
                elif e.key == pygame.K_t: turbo = not turbo
                elif e.key == pygame.K_a:
                    mode = (mode + 1) % 3
                    state = "ready"
                elif e.key == pygame.K_c:
                    wipe_brain(); recent.clear()
                    state = "ready"
                    print("brain wiped — starting from zero")
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    speed_mult = [1.0, 2.0, 4.0, 8.0, 16.0][e.key - pygame.K_1]
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # Click to adjust starting horizontal angle bias
                mode = 1  # Switch to fixed/manual tweak mode
                state = "ready"

        if not paused:
            if turbo:
                for _ in range(TURBO_N):
                    ha, va, sp, si, traj, goal, wall, post = do_kick()
                cur_pts, cur_goal, cur_wall, cur_post = traj, goal, wall, post
                cur_idx = len(cur_pts) - 1
                state = "ready"
            elif state == "ready":
                ha, va, sp, si, traj, goal, wall, post = do_kick()
                cur_action = (ha, va, sp, si)
                cur_pts = traj
                cur_idx = 0.0
                state = "flying"
            elif state == "flying":
                cur_idx += dt_real * speed_mult / DT
                if cur_idx >= len(cur_pts) - 1:
                    cur_idx = float(len(cur_pts) - 1)
                    state = "ready"

        screen.fill((12, 24, 48))
        # Sky gradient
        for y in range(0, 400, 4):
            c = int(18 + 40 * (y / 400))
            pygame.draw.rect(screen, (c // 2, c // 2 + 4, c + 20), (0, y, W, 4))

        draw_pitch(screen, cam)
        draw_goal(screen, cam)
        draw_wall(screen, cam)

        if cur_pts and cur_idx > 0:
            col = (50, 255, 50) if cur_goal else (255, 100, 100) if cur_wall else (255, 215, 0) if cur_post else (255, 165, 70)
            draw_trail(screen, cam, cur_pts, cur_idx, col)
        if cur_pts:
            i = min(int(cur_idx), len(cur_pts) - 1)
            col = (50, 255, 50) if cur_goal else (255, 100, 100) if cur_wall else (255, 215, 0) if cur_post else (255, 165, 70)
            draw_ball(screen, cam, cur_pts[i], col)
        
        draw_kicker(screen, cam, BALL_START_X, BALL_START_Z)
        # Static ball at start pos if ready
        if state == "ready":
            draw_ball(screen, cam, (BALL_START_X, BALL_START_Y, BALL_START_Z), (255, 255, 255))

        goal_pct = (100.0 * goals / shots) if shots else 0.0
        last100 = (sum(recent) / len(recent)) if len(recent) == 100 else None
        last100s = f"{100.0*last100:5.1f}%" if last100 is not None else "  --  "
        mode_names = ["AUTO (directed)", "FIXED", "OPTIMAL"]
        mode_cols = [(200, 215, 240), (200, 215, 240), (255, 215, 100)]

        panel = pygame.Surface((400, 400), pygame.SRCALPHA)
        panel.fill((8, 12, 24, 210))
        screen.blit(panel, (16, 16))
        pygame.draw.rect(screen, (70, 130, 90), pygame.Rect(16, 16, 400, 400), 2)

        y = 24
        screen.blit(f_big.render("3D SOCCER FREE KICK AI", True, (245, 255, 245)), (28, y)); y += 30
        rows = [
            ("SHOTS", f"{shots:>8d}"),
            ("GOALS", f"{goals:>8d}  ({goal_pct:4.1f}%)"),
            ("HIT WALL", f"{hit_wall_count:>8d}"),
            ("HIT POST", f"{hit_post_count:>8d}"),
            ("CONVERSION (100)", f"{last100s:>8}"),
            ("H ANGLE", f"{cur_action[0]:>8.1f} deg"),
            ("V ANGLE", f"{cur_action[1]:>8.1f} deg"),
            ("SPEED", f"{cur_action[2]:>8.1f} m/s"),
            ("SIDE SPIN", f"{cur_action[3]:>8.1f} rad/s"),
        ]
        for k, v in rows:
            screen.blit(f.render(f"{k:<18}{v}", True, (200, 235, 210)), (28, y)); y += 22

        y += 4
        screen.blit(f.render(f"MODE: {mode_names[mode]}", True, mode_cols[mode]), (28, y)); y += 26

        screen.blit(f.render("BEST (h_angle, v_angle, speed, spin):", True, (255, 215, 100)), (28, y)); y += 22
        if shots > 20:
            best_ha, best_va, best_sp, best_si, best_val = best_action(net)
            screen.blit(f.render(f"  H Angle  = {best_ha:5.1f} deg", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  V Angle  = {best_va:5.1f} deg", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  Speed    = {best_sp:5.1f} m/s", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  Side Spin= {best_si:5.1f} rad/s", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  P(Goal)  = {best_val:5.3f}", True, (100, 255, 100)), (28, y)); y += 20
        else:
            screen.blit(f.render("  gathering data...", True, (200, 180, 120)), (28, y))

        if paused: badge, bcol = "PAUSED", (240, 200, 80)
        elif turbo: badge, bcol = "TURBO", (255, 130, 70)
        elif shots < 120: badge, bcol = "PRE-TRAINED", (110, 235, 150)
        elif epsilon() > 0.15: badge, bcol = "LEARNING", (110, 190, 255)
        else: badge, bcol = "FINE-TUNING", (110, 235, 150)

        bw = f.render(badge, True, (12, 14, 22))
        pad = 12
        rect = pygame.Rect(W - 28 - bw.get_width() - 2*pad, 20, bw.get_width() + 2*pad, 34)
        pygame.draw.rect(screen, bcol, rect, border_radius=8)
        screen.blit(bw, (rect.x + pad, rect.y + 7))

        result_text = "GOAL!" if cur_goal else "WALL!" if cur_wall else "POST!" if cur_post else "MISS"
        result_col = (50, 255, 50) if cur_goal else (255, 100, 100) if cur_wall else (255, 215, 0) if cur_post else (200, 200, 200)
        screen.blit(f_big.render(result_text, True, result_col), (W - 150, 60))

        help_txt = "SPACE pause  T turbo  A mode  C wipe  1-5 speed  click=tweak  ESC quit"
        screen.blit(f_s.render(help_txt, True, (140, 175, 160)), (16, H - 26))
        screen.blit(f_s.render(f"brain: {os.path.basename(SAVE_PATH)}", True, (120, 155, 145)), (16, H - 46))

        pygame.display.flip()

    save_brain()
    pygame.quit()
    print(f"\nfinal: {shots} shots | {goals} goals ({100.0*goals/max(1,shots):.1f}%)")
    print("brain saved to", SAVE_PATH)


if __name__ == "__main__":
    main()