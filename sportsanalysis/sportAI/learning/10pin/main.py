#!/usr/bin/env python3
"""
=======================================================================
  3D BOWLING AI  —  ULTRA-FAST STRIKE OPTIMISATION
=======================================================================
  * Full 3D physics (lane friction, realistic ball hook, pin collisions).
  * Official USBC pin spacing and lane dimensions.
  * PHYSICS PRE-TRAINING: Instantly learns ~1000 physics-derived shots 
    before the first frame, giving it immediate "bowling intuition".
  * DIRECTED EXPLORATION: Explores by adding noise to its best guess.
  * Adaptive hill-climbing to "perfect" the strike shot.
  * Brain saves every 100 frames to bowling_brain.pkl

  Controls
  --------
    SPACE   pause/resume
    T       turbo (20 shots/frame)
    A       cycle mode:  AUTO -> FIXED -> OPTIMAL
    C       wipe brain
    1-5     animation speed
    click   set starting position
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
BALL_R             = 0.109   # Bowling ball radius (m) - 8.5 inches
PIN_R              = 0.060   # Pin radius (m) - 4.75 inches diameter
PIN_H              = 0.381   # Pin height (m) - 15 inches
PIN_MASS           = 1.6     # Pin mass (kg)
BALL_MASS          = 7.0     # Ball mass (kg) - ~15 lbs

LANE_LENGTH        = 18.29   # 60 feet in meters
LANE_WIDTH         = 1.07    # 42 inches in meters
FOUL_LINE_Z        = 0.0
HEAD_PIN_Z         = 18.29   # Distance to head pin

# Oil pattern: 0 = slippery (oil), 1 = grippy (dry)
def get_oil_factor(x, z):
    """Returns friction coefficient based on position"""
    if z < 12.0:  # Oiled front part of lane (typically 38-42 feet)
        center_dist = abs(x) / (LANE_WIDTH / 2)
        return 0.15 + 0.10 * center_dist  # 0.15 (middle) to 0.25 (outside)
    else:
        return 0.60  # Dry backend (high friction, causes hook)

ROLLING_FRICTION_BASE = 0.08
HOOK_FACTOR = 4.0      # How much the ball curves in dry conditions

DT      = 0.002
MAX_T   = 6.0

# Action space (REALISTIC ranges)
POS_MIN, POS_MAX     = -0.45, 0.45   # Lateral starting position (m)
ANGLE_MIN, ANG_MAX   = -4.0, 4.0     # Release angle (degrees)
SPD_MIN, SPD_MAX     = 6.0, 9.0      # Ball speed (m/s)

def norm_p(p):  return p / 0.45
def norm_a(a):  return a / 4.0
def norm_s(s):  return (s - 7.5) / 1.5
def den_p(x):   return x * 0.45
def den_a(x):   return x * 4.0
def den_s(x):   return x * 1.5 + 7.5


# =====================================================================
#  PIN PHYSICS
# =====================================================================
class Pin:
    def __init__(self, x, z, pin_id):
        self.x = x
        self.y = PIN_H / 2
        self.z = z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.fallen = False
        self.hit = False
        self.id = pin_id
        self.rotation = 0.0
        self.rot_vel = 0.0
        self.start_x = x
        self.start_z = z
        
    def get_pos(self):
        return (self.x, self.y, self.z)
    
    def update(self, dt):
        if self.fallen and abs(self.vy) < 0.1:
            return
            
        # Gravity
        if self.y > PIN_H / 2 or self.vy < 0:
            self.vy -= G * dt
            
        # Floor collision
        if self.y <= PIN_H / 2:
            self.y = PIN_H / 2
            if self.vy < 0:
                self.vy = -self.vy * 0.3
            self.vx *= 0.92
            self.vz *= 0.92
            
        self.x += self.vx * dt
        self.z += self.vz * dt
        self.y += self.vy * dt
        self.rotation += self.rot_vel * dt
        
        # Check if fallen (moved significantly from starting position)
        if abs(self.x - self.start_x) > 0.05 or abs(self.z - self.start_z) > 0.05:
            self.fallen = True
            
    def reset(self):
        self.fallen = False
        self.hit = False
        self.vx = self.vy = self.vz = 0.0
        self.rotation = 0.0
        self.rot_vel = 0.0


def setup_pins():
    """Create standard 10-pin triangle formation with official USBC spacing"""
    pins = []
    pin_id = 0
    PIN_SPACING = 0.3048  # 12 inches in meters
    row_spacing = PIN_SPACING * math.sqrt(3) / 2  # Height of equilateral triangle
    col_spacing = PIN_SPACING
    
    for row in range(4):
        z = HEAD_PIN_Z - row * row_spacing
        num_pins = row + 1
        start_x = -(num_pins - 1) * col_spacing / 2
        for col in range(num_pins):
            x = start_x + col * col_spacing
            pin = Pin(x, z, pin_id)
            pins.append(pin)
            pin_id += 1
    return pins


# =====================================================================
#  BALL PHYSICS
# =====================================================================
def simulate(start_pos, angle_deg, speed, pins):
    th_rad = math.radians(angle_deg)
    
    x = start_pos
    y = BALL_R
    z = FOUL_LINE_Z
    
    vx = speed * math.sin(th_rad)
    vy = 0.0
    vz = speed * math.cos(th_rad)
    
    spin = 350.0  # RPM
    spin_rad = spin * 2 * math.pi / 60.0
    
    positions = [(x, y, z)]
    t = 0.0
    
    for pin in pins:
        pin.reset()
    
    ball_active = True
    pins_hit = set()
    
    while t < MAX_T and ball_active:
        px, py, pz = x, y, z
        
        oil_factor = get_oil_factor(x, z)
        friction = ROLLING_FRICTION_BASE * oil_factor
        
        ball_speed = math.sqrt(vx*vx + vz*vz)
        
        if ball_speed > 0.5 and z < HEAD_PIN_Z:
            # Hook increases in DRY conditions (high oil_factor)
            hook_strength = HOOK_FACTOR * spin_rad * oil_factor * 0.001
            hook_dir = 1.0 if start_pos < 0 else -1.0  # Right-handed hook towards pocket
            
            vx += hook_dir * hook_strength * DT
            vz *= (1 - friction * DT)
            vx *= (1 - friction * DT)
        
        x += vx * DT
        y += vy * DT
        z += vz * DT
        t += DT
        
        # Gutter logic
        if abs(x) > LANE_WIDTH / 2:
            vx *= 0.90
            vz *= 0.90  # Heavy friction in gutter, no hook
        
        # Pin collisions
        for pin in pins:
            if pin.fallen:
                continue
                
            dx = x - pin.x
            dz = z - pin.z
            dist = math.sqrt(dx*dx + dz*dz)
            
            if dist < BALL_R + PIN_R:
                pins_hit.add(pin.id)
                pin.hit = True
                pin.fallen = True
                
                nx, nz = dx / dist, dz / dist
                relative_vx = vx - pin.vx
                relative_vz = vz - pin.vz
                vn = relative_vx * nx + relative_vz * nz
                
                if vn > 0:  # Moving towards each other
                    # Elastic collision impulse
                    impulse = (1 + 0.4) * vn / (1/BALL_MASS + 1/PIN_MASS)
                    pin.vx += (impulse / PIN_MASS) * nx
                    pin.vz += (impulse / PIN_MASS) * nz
                    vx -= (impulse / BALL_MASS) * nx
                    vz -= (impulse / BALL_MASS) * nz
                    pin.rot_vel = (np.random.random() - 0.5) * 15
        
        # Pin-to-pin collisions (simplified)
        for i, pin1 in enumerate(pins):
            if pin1.fallen:
                for pin2 in pins[i+1:]:
                    if pin2.fallen:
                        dx = pin1.x - pin2.x
                        dz = pin1.z - pin2.z
                        dist = math.sqrt(dx*dx + dz*dz)
                        if dist < PIN_R * 2 and dist > 0.01:
                            nx, nz = dx/dist, dz/dist
                            pin1.vx += nx * 0.8
                            pin1.vz += nz * 0.8
                            pin2.vx -= nx * 0.8
                            pin2.vz -= nz * 0.8
        
        for pin in pins:
            pin.update(DT)
        
        positions.append((x, y, z))
        
        if ball_speed < 1.0 or z > HEAD_PIN_Z + 2.0:
            ball_active = False
    
    pins_down = len(pins_hit)
    strike = (pins_down == 10)
    
    return positions, pins_down, strike, pins_hit


# =====================================================================
#  NEURAL NET
# =====================================================================
class Net:
    def __init__(self, n_in=3, h=64, seed=1, lr=2.5e-3):
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

def evaluate_pins(net, pos, angle, speed):
    X = np.array([[norm_p(pos), norm_a(angle), norm_s(speed)]], dtype=np.float64)
    pred = float(net.forward(X)[0, 0])
    return pred * 10  # Predict pins knocked down (0-10)


def refine_strike_shot(net, pos, start_angle, start_speed, max_iters=80):
    current_angle = float(np.clip(start_angle, ANGLE_MIN, ANG_MAX))
    current_speed = float(np.clip(start_speed, SPD_MIN, SPD_MAX))
    current_pins = evaluate_pins(net, pos, current_angle, current_speed)
    
    step_angle = 0.5
    step_speed = 0.2
    min_step_angle = 0.05
    min_step_speed = 0.02
    
    for _ in range(max_iters):
        neighbors = [
            (current_angle + step_angle, current_speed),
            (current_angle - step_angle, current_speed),
            (current_angle, current_speed + step_speed),
            (current_angle, current_speed - step_speed),
            (current_angle + step_angle, current_speed + step_speed),
            (current_angle - step_angle, current_speed - step_speed),
        ]
        
        best_angle, best_speed, best_pins = current_angle, current_speed, current_pins
        
        for n_angle, n_speed in neighbors:
            n_angle = float(np.clip(n_angle, ANGLE_MIN, ANG_MAX))
            n_speed = float(np.clip(n_speed, SPD_MIN, SPD_MAX))
            pins = evaluate_pins(net, pos, n_angle, n_speed)
            if pins > best_pins:
                best_pins = pins
                best_angle = n_angle
                best_speed = n_speed
        
        if best_pins > current_pins:
            current_angle, current_speed, current_pins = best_angle, best_speed, best_pins
        else:
            step_angle *= 0.5
            step_speed *= 0.5
        
        if step_angle < min_step_angle and step_speed < min_step_speed:
            break
    
    return current_angle, current_speed, current_pins


def best_action(net, pos, n_starts=3):
    angles = np.arange(ANGLE_MIN, ANG_MAX + 1e-6, 0.5)
    speeds = np.arange(SPD_MIN, SPD_MAX + 1e-6, 0.2)
    A, S = np.meshgrid(angles, speeds)
    A = A.ravel(); S = S.ravel()
    
    Xc = np.column_stack([np.full_like(A, norm_p(pos)), norm_a(A), norm_s(S)])
    preds = net.forward(Xc).ravel() * 10
    order = np.argsort(preds)[-n_starts:]
    
    best_overall_angle, best_overall_speed, best_overall_pins = None, None, -1
    for i in order:
        angle, speed, pins = refine_strike_shot(net, pos, A[i], S[i])
        if pins > best_overall_pins:
            best_overall_pins = pins
            best_overall_angle = angle
            best_overall_speed = speed
    
    return float(best_overall_angle), float(best_overall_speed), float(best_overall_pins)


# =====================================================================
#  GLOBAL STATE & PRE-TRAINING
# =====================================================================
BUFSIZE = 40000
net     = Net()
buf_X   = np.zeros((BUFSIZE, 3))
buf_Y   = np.zeros((BUFSIZE, 1))
buf_n   = 0
buf_ptr = 0
rng     = np.random.default_rng(12345)
frames  = 0
strikes = 0
total_pins = 0
spares = 0

CAL_BINS = 50
cal_strikes    = np.zeros(CAL_BINS, dtype=np.float64)
cal_attempts   = np.zeros(CAL_BINS, dtype=np.float64)

def cal_bin_index(pred_pins):
    return int(np.clip(pred_pins / 10 * CAL_BINS, 0, CAL_BINS - 1))

BIN_W  = 0.1
N_BINS = int((POS_MAX - POS_MIN) / BIN_W) + 1
bin_strikes   = np.zeros(N_BINS, dtype=np.int64)
bin_attempts  = np.zeros(N_BINS, dtype=np.int64)

def bin_idx(p): return max(0, min(N_BINS - 1, int((p - POS_MIN) / BIN_W)))

SAVE_PATH = os.path.join(os.getcwd(), "bowling_brain.pkl")

def epsilon(): return max(0.05, 0.80 * math.exp(-frames / 250.0))


def add_sample(pos, angle, speed, pins_down):
    global buf_n, buf_ptr
    buf_X[buf_ptr, 0] = norm_p(pos)
    buf_X[buf_ptr, 1] = norm_a(angle)
    buf_X[buf_ptr, 2] = norm_s(speed)
    buf_Y[buf_ptr, 0] = pins_down / 10.0
    buf_ptr = (buf_ptr + 1) % BUFSIZE
    if buf_n < BUFSIZE: buf_n += 1


def train_steps(k=2, batch=128):
    if buf_n < 64: return
    for _ in range(k):
        idx = rng.integers(0, buf_n, size=min(batch, buf_n))
        net.train_batch(buf_X[idx], buf_Y[idx])


def choose_action(pos, greedy=False):
    best_angle, best_speed, _ = best_action(net, pos)
    
    if not greedy and (frames < 120 or rng.random() < epsilon()):
        noise_angle = 1.0 * epsilon() + 0.2
        noise_speed = 0.3 * epsilon() + 0.1
        
        angle = best_angle + rng.normal(0.0, noise_angle)
        speed = best_speed + rng.normal(0.0, noise_speed)
    else:
        angle = best_angle
        speed = best_speed
    
    return (float(np.clip(angle, ANGLE_MIN, ANG_MAX)),
            float(np.clip(speed, SPD_MIN, SPD_MAX)))


def pretrain_brain():
    print("Pre-training brain with bowling physics priors...")
    for _ in range(1200):
        pos = rng.uniform(POS_MIN, POS_MAX)
        # Ideal: aim for pocket (between 1-3 pins for righties)
        # If starting left (pos < 0), angle should be positive (rightward)
        base_angle = 2.5 if pos < 0 else -2.5
        angle = base_angle + rng.normal(0, 1.0)
        speed = rng.normal(7.5, 0.5)
        
        angle = float(np.clip(angle, ANGLE_MIN, ANG_MAX))
        speed = float(np.clip(speed, SPD_MIN, SPD_MAX))
        
        pins = setup_pins()
        _, pins_down, _, _ = simulate(pos, angle, speed, pins)
        add_sample(pos, angle, speed, pins_down)
    
    for _ in range(60):
        train_steps(k=5, batch=256)
    print("Pre-training complete. AI has bowling intuition!")


# =====================================================================
#  JOINT OPTIMISER
# =====================================================================
opt_cache = {"result": None, "at_frame": -10**9}

def find_optimal_jointly():
    if frames < 20:
        return None
    pos_grid = np.linspace(POS_MIN, POS_MAX, 20)
    best = None
    for pos in pos_grid:
        angle, speed, pred_pins = best_action(net, pos)
        strike_prob = max(0, (pred_pins - 8) / 2)
        if best is None or strike_prob > best[3]:
            best = (float(pos), float(angle), float(speed), float(strike_prob), float(pred_pins))
    return best


def get_optimal(force=False, refresh_every=15):
    if not force and frames - opt_cache["at_frame"] < refresh_every:
        return opt_cache["result"]
    opt_cache["result"] = find_optimal_jointly()
    opt_cache["at_frame"] = frames
    return opt_cache["result"]


# =====================================================================
#  SAVE / LOAD
# =====================================================================
def save_brain():
    data = {
        "params": [p.copy() for p in net.params], "adam_m": [m.copy() for m in net.m],
        "adam_v": [v.copy() for v in net.v], "adam_t": net.t,
        "buf_X": buf_X, "buf_Y": buf_Y, "buf_n": buf_n, "buf_ptr": buf_ptr,
        "frames": frames, "strikes": strikes, "total_pins": total_pins, "spares": spares,
        "cal_strikes": cal_strikes, "cal_attempts": cal_attempts,
        "bin_strikes": bin_strikes, "bin_attempts": bin_attempts,
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
    global buf_X, buf_Y, buf_n, buf_ptr, frames, strikes, total_pins, spares
    global cal_strikes, cal_attempts, bin_strikes, bin_attempts
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
        frames = data["frames"]
        strikes = data["strikes"]
        total_pins = data["total_pins"]
        spares = data.get("spares", 0)
        cal_strikes = data.get("cal_strikes", np.zeros(CAL_BINS))
        cal_attempts = data.get("cal_attempts", np.zeros(CAL_BINS))
        bin_strikes = data.get("bin_strikes", np.zeros(N_BINS, dtype=np.int64))
        bin_attempts = data.get("bin_attempts", np.zeros(N_BINS, dtype=np.int64))
        return True
    except Exception as e:
        print("load failed:", e); return False


def wipe_brain():
    global net, buf_X, buf_Y, buf_n, buf_ptr, frames, strikes, total_pins, spares
    global cal_strikes, cal_attempts, bin_strikes, bin_attempts
    net = Net()
    buf_X = np.zeros((BUFSIZE, 3)); buf_Y = np.zeros((BUFSIZE, 1))
    buf_n = buf_ptr = 0
    frames = strikes = total_pins = spares = 0
    cal_strikes[:] = 0.0; cal_attempts[:] = 0.0
    bin_strikes[:] = 0; bin_attempts[:] = 0
    opt_cache["result"] = None; opt_cache["at_frame"] = -10**9
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

def draw_lane(screen, cam, optimal_pos=None):
    poly3(screen, cam, 
          [(-LANE_WIDTH/2, 0, 0), (LANE_WIDTH/2, 0, 0), 
           (LANE_WIDTH/2, 0, LANE_LENGTH), (-LANE_WIDTH/2, 0, LANE_LENGTH)],
          fill=(180, 140, 90), outline=(120, 90, 60), width=2)
    
    for side in [-1, 1]:
        gutter_x = side * (LANE_WIDTH/2 + 0.15)
        poly3(screen, cam,
              [(gutter_x - 0.15, -0.05, 0), (gutter_x + 0.15, -0.05, 0),
               (gutter_x + 0.15, -0.05, LANE_LENGTH), (gutter_x - 0.15, -0.05, LANE_LENGTH)],
              fill=(30, 30, 40), outline=(20, 20, 30), width=1)
    
    poly3(screen, cam,
          [(-LANE_WIDTH/2, 0, -2), (LANE_WIDTH/2, 0, -2),
           (LANE_WIDTH/2, 0, 0), (-LANE_WIDTH/2, 0, 0)],
          fill=(160, 120, 70), outline=(100, 80, 50), width=2)
    
    line3(screen, cam, (-LANE_WIDTH/2, 0.01, 0), (LANE_WIDTH/2, 0.01, 0), (255, 255, 255), 3)
    
    for i, arrow_z in enumerate([7.5, 8.0, 8.5]):
        for side in [-1, 1]:
            arrow_x = side * (0.2 + i * 0.1)
            poly3(screen, cam,
                  [(arrow_x - 0.03, 0.005, arrow_z - 0.05),
                   (arrow_x + 0.03, 0.005, arrow_z - 0.05),
                   (arrow_x, 0.005, arrow_z + 0.05)],
                  fill=(100, 80, 60))
    
    if optimal_pos is not None:
        line3(screen, cam, (optimal_pos, 0.01, -1.5), (optimal_pos, 0.01, 0), (255, 215, 0), 4)


def draw_pins(screen, cam, pins):
    for pin in pins:
        if pin.fallen:
            angle = pin.rotation
            end_x = pin.x + math.cos(angle) * PIN_H
            end_z = pin.z + math.sin(angle) * PIN_H
            line3(screen, cam, (pin.x, 0.05, pin.z), (end_x, 0.05, end_z), (255, 255, 255), 4)
        else:
            base = (pin.x, 0, pin.z)
            top = (pin.x, PIN_H, pin.z)
            line3(screen, cam, base, top, (255, 255, 255), 6)
            pr = cam.project(top)
            if pr:
                rad = max(3, int(cam.radius(top, PIN_R * 0.8) or 3))
                pygame.draw.circle(screen, (255, 255, 255), (int(pr[0]), int(pr[1])), rad)


def draw_ball(screen, cam, pos, color=(255, 100, 100)):
    pr = cam.project(pos)
    if pr is None: return
    rad = cam.radius(pos, BALL_R)
    if rad is None or rad < 1: return
    pygame.draw.circle(screen, color, (int(pr[0]), int(pr[1])), int(rad))
    pygame.draw.circle(screen, (0, 0, 0), (int(pr[0]), int(pr[1])), max(1, int(rad)), 2)
    
    if rad > 5:
        for i in range(3):
            angle = i * 2.094
            hx = int(pr[0] + rad * 0.4 * math.cos(angle))
            hy = int(pr[1] + rad * 0.4 * math.sin(angle))
            pygame.draw.circle(screen, (40, 40, 40), (hx, hy), max(1, int(rad * 0.15)))


def draw_trail(screen, cam, pts, idx, color):
    n = max(2, int(idx))
    prev = None
    for i in range(min(n, len(pts))):
        pr = cam.project(pts[i])
        if pr is None: prev = None; continue
        if prev is not None: 
            pygame.draw.line(screen, color, prev, (int(pr[0]), int(pr[1])), 2)
        prev = (int(pr[0]), int(pr[1]))


def draw_bowler(screen, cam, pos):
    base = (pos, 0, -1.5)
    torso_top = (pos, 1.4, -1.5)
    arm_end = (pos, 0.8, -0.8)
    
    line3(screen, cam, base, (pos - 0.15, 0.8, -1.5), (30, 60, 150), 6)
    line3(screen, cam, base, (pos + 0.15, 0.8, -1.5), (30, 60, 150), 6)
    line3(screen, cam, (pos, 0.8, -1.5), torso_top, (30, 60, 150), 8)
    
    pr = cam.project(torso_top)
    if pr:
        rad = max(5, int(cam.radius(torso_top, 0.12) or 5))
        pygame.draw.circle(screen, (255, 220, 180), (int(pr[0]), int(pr[1])), rad)
    
    line3(screen, cam, (pos, 1.2, -1.5), arm_end, (30, 60, 150), 5)


# =====================================================================
#  MAIN
# =====================================================================
def main():
    global frames, strikes, total_pins, spares, cal_attempts, cal_strikes

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("3D Bowling AI — STRIKE OPTIMISATION")
    clock = pygame.time.Clock()

    try:
        f_big = pygame.font.SysFont("consolas,couriernew,monospace", 22, bold=True)
        f     = pygame.font.SysFont("consolas,couriernew,monospace", 18, bold=True)
        f_s   = pygame.font.SysFont("consolas,couriernew,monospace", 14)
    except Exception:
        f_big = pygame.font.Font(None, 26)
        f     = pygame.font.Font(None, 22)
        f_s   = pygame.font.Font(None, 16)

    cam = Camera((0.0, 3.5, -4.0), (0.0, 0.5, 10.0), fov=65)

    # Delete old brain so it doesn't load the failed 0.01 avg pins data
    if os.path.exists(SAVE_PATH):
        try:
            os.remove(SAVE_PATH)
            print("Deleted old brain file to start fresh with corrected physics.")
        except OSError:
            pass

    loaded = load_brain()
    if not loaded:
        pretrain_brain()
    else:
        print("loaded existing brain")

    pins = setup_pins()
    state, cur_pos, cur_pts, cur_idx = "ready", 0.0, [], 0.0
    cur_pins_down, cur_strike = 0, False
    cur_action = (0.0, 8.0)
    turbo, paused, speed_mult, mode, fixed_pos = False, False, 1.0, 0, 0.0
    recent, TURBO_N = deque(maxlen=100), 20

    def do_bowl(pos=None, angle=None, speed=None, greedy=False):
        nonlocal cur_pins_down, cur_strike
        global frames, strikes, total_pins, spares, cal_attempts, cal_strikes

        if pos is None:
            if mode == 2:
                opt = get_optimal()
                if opt is not None:
                    pos, angle, speed = opt[0], opt[1], opt[2]
                    greedy = True
                else:
                    pos = float(rng.uniform(POS_MIN, POS_MAX))
            elif mode == 1:
                pos = fixed_pos
            else:
                pos = float(rng.uniform(POS_MIN, POS_MAX))

        if angle is None or speed is None:
            angle, speed = choose_action(pos, greedy=greedy)

        trajectory, pins_down, strike, pins_hit = simulate(pos, angle, speed, pins)
        add_sample(pos, angle, speed, pins_down)

        k = 5 if frames < 500 else 2
        batch = 256 if frames < 500 else 128
        train_steps(k=k, batch=batch)

        frames += 1
        total_pins += pins_down
        cur_pins_down = pins_down
        cur_strike = strike

        if strike:
            strikes += 1
            bin_strikes[bin_idx(pos)] += 1
        bin_attempts[bin_idx(pos)] += 1

        pred_pins = float(net.forward(np.array([[norm_p(pos), norm_a(angle), norm_s(speed)]]))[0, 0]) * 10
        bi = cal_bin_index(pred_pins)
        cal_attempts[bi] += 1.0
        if strike:
            cal_strikes[bi] += 1.0

        recent.append(1 if strike else 0)

        if frames % 100 == 0:
            save_brain()
            cal_attempts *= 0.7
            cal_strikes *= 0.7
            print(f"  [{frames:5d} frames | {strikes} strikes | "
                  f"{total_pins/frames:.2f} avg pins | {100.0*strikes/frames:5.1f}%] saved")

        return pos, angle, speed, trajectory, pins_down, strike

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
                    if mode == 2: get_optimal(force=True)
                elif e.key == pygame.K_c:
                    wipe_brain(); recent.clear()
                    state = "ready"
                    print("brain wiped — starting from zero")
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    speed_mult = [1.0, 2.0, 4.0, 8.0, 16.0][e.key - pygame.K_1]
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx = e.pos[0]
                frac = max(0.0, min(1.0, (mx - 500) / 700.0))
                fixed_pos = float(np.clip(POS_MIN + frac * (POS_MAX - POS_MIN), POS_MIN, POS_MAX))
                mode = 1
                state = "ready"

        if not paused:
            if turbo:
                for _ in range(TURBO_N):
                    pos, angle, speed, traj, pins_down, strike = do_bowl()
                cur_pos, cur_pts, cur_pins_down, cur_strike = pos, traj, pins_down, strike
                cur_idx = len(cur_pts) - 1
                state = "ready"
            elif state == "ready":
                pos, angle, speed, traj, pins_down, strike = do_bowl()
                cur_pos, cur_pts = pos, traj
                cur_action = (angle, speed)
                cur_pins_down, cur_strike = pins_down, strike
                cur_idx = 0.0
                state = "rolling"
            elif state == "rolling":
                cur_idx += dt_real * speed_mult / DT
                if cur_idx >= len(cur_pts) - 1:
                    cur_idx = float(len(cur_pts) - 1)
                    state = "ready"

        opt = get_optimal()

        screen.fill((20, 20, 30))
        for y in range(0, 340, 4):
            c = int(18 + 30 * (y / 340))
            pygame.draw.rect(screen, (c // 2, c // 2 + 4, c + 20), (0, y, W, 4))

        draw_lane(screen, cam, optimal_pos=(opt[0] if opt else None))
        draw_pins(screen, cam, pins)

        if cur_pts and cur_idx > 0:
            col = (50, 255, 50) if cur_strike else (255, 215, 0) if cur_pins_down >= 8 else (255, 165, 70)
            draw_trail(screen, cam, cur_pts, cur_idx, col)
        if cur_pts:
            i = min(int(cur_idx), len(cur_pts) - 1)
            col = (50, 255, 50) if cur_strike else (255, 215, 0) if cur_pins_down >= 8 else (255, 165, 70)
            draw_ball(screen, cam, cur_pts[i], col)
        draw_bowler(screen, cam, cur_pos)

        strike_pct = (100.0 * strikes / frames) if frames else 0.0
        avg_pins = total_pins / frames if frames else 0.0
        last100 = (sum(recent) / len(recent)) if len(recent) == 100 else None
        last100s = f"{100.0*last100:5.1f}%" if last100 is not None else "  --  "
        mode_names = ["AUTO (directed)", "FIXED", "OPTIMAL"]
        mode_cols = [(200, 215, 240), (200, 215, 240), (255, 215, 100)]

        panel = pygame.Surface((400, 380), pygame.SRCALPHA)
        panel.fill((8, 12, 24, 210))
        screen.blit(panel, (16, 16))
        pygame.draw.rect(screen, (70, 90, 130), pygame.Rect(16, 16, 400, 380), 2)

        y = 24
        screen.blit(f_big.render("3D BOWLING AI", True, (245, 245, 255)), (28, y)); y += 30
        rows = [
            ("FRAMES", f"{frames:>8d}"),
            ("STRIKES", f"{strikes:>8d}  ({strike_pct:4.1f}%)"),
            ("AVG PINS", f"{avg_pins:>8.2f}"),
            ("STRIKE % (100)", f"{last100s:>8}"),
            ("CUR POS", f"{cur_pos:>8.2f} m"),
            ("CUR ANGLE", f"{cur_action[0]:>8.1f} deg"),
            ("CUR SPEED", f"{cur_action[1]:>8.2f} m/s"),
            ("PINS DOWN", f"{cur_pins_down:>8d}"),
        ]
        for k, v in rows:
            screen.blit(f.render(f"{k:<18}{v}", True, (200, 215, 240)), (28, y)); y += 22

        y += 4
        screen.blit(f.render(f"MODE: {mode_names[mode]}", True, mode_cols[mode]), (28, y)); y += 26

        screen.blit(f.render("BEST (pos, angle, speed) FOR STRIKE:", True, (255, 215, 100)), (28, y)); y += 22
        if opt is not None:
            pos_, a_, s_, strike_prob_, pins_ = opt
            screen.blit(f.render(f"  position = {pos_:5.2f} m", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  angle = {a_:5.1f} deg", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  speed = {s_:5.2f} m/s", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  P(strike) = {strike_prob_:5.3f}", True, (100, 255, 100)), (28, y)); y += 20
            screen.blit(f.render(f"  Expected pins = {pins_:5.2f}", True, (255, 215, 100)), (28, y)); y += 20
        else:
            screen.blit(f.render("  gathering data...", True, (200, 180, 120)), (28, y))

        if paused: badge, bcol = "PAUSED", (240, 200, 80)
        elif turbo: badge, bcol = "TURBO", (255, 130, 70)
        elif frames < 120: badge, bcol = "PRE-TRAINED", (110, 235, 150)
        elif epsilon() > 0.15: badge, bcol = "LEARNING", (110, 190, 255)
        else: badge, bcol = "FINE-TUNING", (110, 235, 150)

        bw = f.render(badge, True, (12, 14, 22))
        pad = 12
        rect = pygame.Rect(W - 28 - bw.get_width() - 2*pad, 20, bw.get_width() + 2*pad, 34)
        pygame.draw.rect(screen, bcol, rect, border_radius=8)
        screen.blit(bw, (rect.x + pad, rect.y + 7))

        result_text = "STRIKE!" if cur_strike else f"{cur_pins_down} PINS" if cur_pins_down > 0 else "GUTTER"
        result_col = (50, 255, 50) if cur_strike else (255, 215, 0) if cur_pins_down >= 8 else (255, 100, 100)
        screen.blit(f_big.render(result_text, True, result_col), (W - 200, 60))

        help_txt = "SPACE pause  T turbo  A mode  C wipe  1-5 speed  click=position  ESC quit"
        screen.blit(f_s.render(help_txt, True, (140, 155, 180)), (16, H - 26))
        screen.blit(f_s.render(f"brain: {os.path.basename(SAVE_PATH)}", True, (120, 135, 165)), (16, H - 46))

        pygame.display.flip()

    save_brain()
    pygame.quit()
    print(f"\nfinal: {frames} frames | {strikes} strikes "
          f"({100.0*strikes/max(1,frames):.1f}%) | {total_pins/frames:.2f} avg pins")
    print("brain saved to", SAVE_PATH)


if __name__ == "__main__":
    main()