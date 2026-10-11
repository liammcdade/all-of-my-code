#!/usr/bin/env python3
"""
=======================================================================
  3D GOLF AI  —  ULTRA-FAST PUTT/CHIP OPTIMISATION
=======================================================================
  * Full 3D physics (gravity, drag, rolling friction, hole capture).
  * PHYSICS PRE-TRAINING: Instantly learns ~1000 physics-derived shots 
    before the first frame, giving it immediate "golf intuition".
  * DIRECTED EXPLORATION: Explores by adding noise to its best guess, 
    rather than blind random guessing.
  * Adaptive hill-climbing to "perfect" the shot combination.
  * Brain saves every 100 strokes to golf_brain.pkl

  Controls
  --------
    SPACE   pause/resume
    T       turbo (20 shots/frame)
    A       cycle mode:  AUTO -> FIXED -> OPTIMAL
    C       wipe brain
    1-5     animation speed
    click   aim / set fixed distance
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
DRAG_K             = 0.020
BALL_R             = 0.02135  # Golf ball radius (m)
HOLE_R             = 0.054    # Golf hole radius (m)
ROLLING_FRICTION   = 0.12     # Deceleration on green (m/s^2)
BOUNCE_RESTITUTION = 0.40

DT      = 0.002
MAX_T   = 8.0

D_MIN, D_MAX     = 2.0, 20.0
ANG_MIN, ANG_MAX = -15.0, 15.0  # Horizontal aim deviation (degrees)
SPD_MIN, SPD_MAX = 1.0, 15.0

TARGET_CAP = 2.0  # Max miss distance we care to optimize (m)

def norm_d(d):  return (d - 11.0) / 9.0
def norm_a(a):  return (a - 0.0) / 15.0
def norm_s(s):  return (s - 8.0) / 7.0
def den_a(x):   return x * 15.0 + 0.0
def den_s(x):   return x * 7.0 + 8.0


def simulate(d, theta_deg, speed):
    elev_rad = math.radians(6.0)  # Fixed slight loft for chip/putt hybrid
    th_rad = math.radians(theta_deg)
    
    x, y, z = d, BALL_R, 0.0
    vx = -speed * math.cos(elev_rad) * math.cos(th_rad)
    vy =  speed * math.sin(elev_rad)
    vz =  speed * math.cos(elev_rad) * math.sin(th_rad)
    
    positions = [(x, y, z)]
    t = 0.0
    made = False
    min_d2 = x*x + z*z
    
    while t < MAX_T:
        px, py, pz = x, y, z
        
        # Air drag
        s = math.sqrt(vx*vx + vy*vy + vz*vz)
        if s > 0:
            vx += -DRAG_K * s * vx * DT
            vy += (-G - DRAG_K * s * vy) * DT
            vz += -DRAG_K * s * vz * DT
            
        x += vx * DT
        y += vy * DT
        z += vz * DT
        t += DT
        
        dist_xz2 = x*x + z*z
        if dist_xz2 < min_d2:
            min_d2 = dist_xz2
            
        # Ground collision
        if y <= BALL_R:
            y = BALL_R
            v_horiz = math.sqrt(vx*vx + vz*vz)
            
            # Hole capture logic: over the hole and moving slowly enough
            if math.sqrt(dist_xz2) < HOLE_R and v_horiz < 2.5:
                made = True
                min_d2 = 0.0
                positions.append((x, y, z))
                break
                
            if vy < -0.1:
                vy = -vy * BOUNCE_RESTITUTION
                vx *= 0.85  # Bounce friction
                vz *= 0.85
            else:
                vy = 0.0
                
            # Rolling friction
            if v_horiz > 0:
                decel = ROLLING_FRICTION * DT
                if v_horiz <= decel:
                    vx = 0.0
                    vz = 0.0
                else:
                    vx -= (vx / v_horiz) * decel
                    vz -= (vz / v_horiz) * decel
                    
        positions.append((x, y, z))
        
        # Stop if completely still
        if abs(vx) < 0.01 and abs(vy) < 0.01 and abs(vz) < 0.01 and y <= BALL_R + 0.01:
            break
            
        # Out of bounds safety break
        if x > 30 or x < -5 or abs(z) > 20:
            break

    return positions, math.sqrt(min_d2), made


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

def evaluate_miss(net, d, th, sv):
    X = np.array([[norm_d(d), norm_a(th), norm_s(sv)]], dtype=np.float64)
    pred = float(net.forward(X)[0, 0])
    return pred * TARGET_CAP


def refine_perfect_shot(net, d, start_th, start_sv, max_iters=80):
    current_th = float(np.clip(start_th, ANG_MIN, ANG_MAX))
    current_sv = float(np.clip(start_sv, SPD_MIN, SPD_MAX))
    current_miss = evaluate_miss(net, d, current_th, current_sv)
    
    step_th = 2.0
    step_sv = 0.4
    min_step_th = 0.02
    min_step_sv = 0.01
    
    for _ in range(max_iters):
        neighbors = [
            (current_th + step_th, current_sv), (current_th - step_th, current_sv),
            (current_th, current_sv + step_sv), (current_th, current_sv - step_sv),
            (current_th + step_th, current_sv + step_sv), (current_th - step_th, current_sv - step_sv),
            (current_th + step_th, current_sv - step_sv), (current_th - step_th, current_sv + step_sv),
        ]
        
        best_th, best_sv, best_miss = current_th, current_sv, current_miss
        
        for n_th, n_sv in neighbors:
            n_th = float(np.clip(n_th, ANG_MIN, ANG_MAX))
            n_sv = float(np.clip(n_sv, SPD_MIN, SPD_MAX))
            if n_th == current_th and n_sv == current_sv:
                continue
            miss = evaluate_miss(net, d, n_th, n_sv)
            if miss < best_miss:
                best_miss = miss
                best_th = n_th
                best_sv = n_sv
                
        if best_miss < current_miss:
            current_th, current_sv, current_miss = best_th, best_sv, best_miss
        else:
            step_th *= 0.5
            step_sv *= 0.5
            
        if step_th < min_step_th and step_sv < min_step_sv:
            break
            
    return current_th, current_sv, current_miss


def best_action(net, d, n_starts=3):
    angs = np.arange(ANG_MIN, ANG_MAX + 1e-6, 2.0)
    spds = np.arange(SPD_MIN, SPD_MAX + 1e-6, 0.5)
    A, S = np.meshgrid(angs, spds)
    A = A.ravel(); S = S.ravel()
    
    Xc = np.column_stack([np.full_like(A, norm_d(d)), norm_a(A), norm_s(S)])
    preds = net.forward(Xc).ravel() * TARGET_CAP
    order = np.argsort(preds)[:n_starts]
    
    best_overall_th, best_overall_sv, best_overall_miss = None, None, float('inf')
    for i in order:
        th, sv, miss = refine_perfect_shot(net, d, A[i], S[i])
        if miss < best_overall_miss:
            best_overall_miss = miss
            best_overall_th = th
            best_overall_sv = sv
            
    return float(best_overall_th), float(best_overall_sv), float(best_overall_miss)


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
throws  = 0
makes   = 0
total_miss = 0.0

CAL_BINS = 50
CAL_MAX  = 2.0
cal_makes    = np.zeros(CAL_BINS, dtype=np.float64)
cal_attempts = np.zeros(CAL_BINS, dtype=np.float64)

def cal_bin_index(pm):
    return int(np.clip(pm / CAL_MAX * CAL_BINS, 0, CAL_BINS - 1))

def calibration_lookup(pred_miss, sigma_bins=2.5):
    bi = cal_bin_index(pred_miss)
    idx = np.arange(CAL_BINS)
    w = np.exp(-0.5 * ((idx - bi) / sigma_bins) ** 2)
    a = float((cal_attempts * w).sum())
    if a < 8.0:
        return float(1.0 / (1.0 + math.exp((pred_miss - HOLE_R) / 0.05)))
    m = float((cal_makes * w).sum())
    return m / a

BIN_W  = 1.0
N_BINS = int(math.floor((D_MAX - D_MIN) / BIN_W)) + 1
bin_makes    = np.zeros(N_BINS, dtype=np.int64)
bin_attempts = np.zeros(N_BINS, dtype=np.int64)

def bin_idx(d): return max(0, min(N_BINS - 1, int((d - D_MIN) / BIN_W)))

SAVE_PATH = os.path.join(os.getcwd(), "golf_brain.pkl")

def epsilon(): return max(0.05, 0.80 * math.exp(-throws / 250.0))
def noise_scale(): return max(0.02, math.exp(-throws / 800.0))


def add_sample(d, th, sv, min_d):
    global buf_n, buf_ptr
    buf_X[buf_ptr, 0] = norm_d(d)
    buf_X[buf_ptr, 1] = norm_a(th)
    buf_X[buf_ptr, 2] = norm_s(sv)
    buf_Y[buf_ptr, 0] = min(min_d, TARGET_CAP) / TARGET_CAP
    buf_ptr = (buf_ptr + 1) % BUFSIZE
    if buf_n < BUFSIZE: buf_n += 1


def train_steps(k=2, batch=128):
    if buf_n < 64: return
    for _ in range(k):
        idx = rng.integers(0, buf_n, size=min(batch, buf_n))
        net.train_batch(buf_X[idx], buf_Y[idx])


def choose_action(d, greedy=False):
    best_th, best_sv, _ = best_action(net, d)
    
    if not greedy and (throws < 120 or rng.random() < epsilon()):
        noise_th = 6.0 * epsilon() + 1.0
        noise_sv = 1.5 * epsilon() + 0.3
        
        th = best_th + rng.normal(0.0, noise_th)
        sv = best_sv + rng.normal(0.0, noise_sv)
    else:
        th = best_th
        sv = best_sv
        
    return (float(np.clip(th, ANG_MIN, ANG_MAX)),
            float(np.clip(sv, SPD_MIN, SPD_MAX)))


def pretrain_brain():
    print("Pre-training brain with golf physics priors...")
    for _ in range(1200):
        d = rng.uniform(D_MIN, D_MAX)
        ideal_speed = d / 1.2
        speed = rng.normal(ideal_speed, 1.0)
        speed = float(np.clip(speed, SPD_MIN, SPD_MAX))
        
        theta = rng.normal(0.0, 2.0)
        theta = float(np.clip(theta, ANG_MIN, ANG_MAX))
        
        _, min_d, made = simulate(d, theta, speed)
        add_sample(d, theta, speed, min_d)
    
    for _ in range(60):
        train_steps(k=5, batch=256)
    print("Pre-training complete. AI has golf intuition!")


# =====================================================================
#  JOINT OPTIMISER
# =====================================================================
opt_cache = {"result": None, "at_throw": -10**9}

def find_optimal_jointly():
    if throws < 20:  
        return None
    d_grid = np.linspace(D_MIN, D_MAX, 28)
    best = None
    for d in d_grid:
        a, s, pn = best_action(net, d)
        pm = float(pn) * TARGET_CAP
        pmake = calibration_lookup(pm)
        ep = pmake  # Expected make probability (1 point per make)
        if best is None or ep > best[3]:
            best = (float(d), float(a), float(s), float(ep), float(pmake), float(pm))
    return best


def get_optimal(force=False, refresh_every=15):
    if not force and throws - opt_cache["at_throw"] < refresh_every:
        return opt_cache["result"]
    opt_cache["result"]   = find_optimal_jointly()
    opt_cache["at_throw"] = throws
    return opt_cache["result"]


# =====================================================================
#  SAVE / LOAD
# =====================================================================
def save_brain():
    data = {
        "params": [p.copy() for p in net.params], "adam_m": [m.copy() for m in net.m],
        "adam_v": [v.copy() for v in net.v], "adam_t": net.t,
        "buf_X": buf_X, "buf_Y": buf_Y, "buf_n": buf_n, "buf_ptr": buf_ptr,
        "throws": throws, "makes": makes, "total_miss": total_miss,
        "cal_makes": cal_makes, "cal_attempts": cal_attempts,
        "bin_makes": bin_makes, "bin_attempts": bin_attempts,
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
    global buf_X, buf_Y, buf_n, buf_ptr, throws, makes, total_miss
    global cal_makes, cal_attempts, bin_makes, bin_attempts
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
        throws, makes = data["throws"], data["makes"]
        total_miss = data.get("total_miss", 0.0)
        cal_makes = data.get("cal_makes", np.zeros(CAL_BINS))
        cal_attempts = data.get("cal_attempts", np.zeros(CAL_BINS))
        bin_makes = data.get("bin_makes", np.zeros(N_BINS, dtype=np.int64))
        bin_attempts = data.get("bin_attempts", np.zeros(N_BINS, dtype=np.int64))
        return True
    except Exception as e:
        print("load failed:", e); return False


def wipe_brain():
    global net, buf_X, buf_Y, buf_n, buf_ptr, throws, makes, total_miss
    global cal_makes, cal_attempts, bin_makes, bin_attempts
    net = Net()
    buf_X = np.zeros((BUFSIZE, 3)); buf_Y = np.zeros((BUFSIZE, 1))
    buf_n = buf_ptr = 0
    throws = makes = 0; total_miss = 0.0
    cal_makes[:] = 0.0; cal_attempts[:] = 0.0
    bin_makes[:] = 0; bin_attempts[:] = 0
    opt_cache["result"] = None; opt_cache["at_throw"] = -10**9
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

def draw_green(screen, cam, optimal_d=None):
    # Green surface
    poly3(screen, cam, [(-2, 0, -10), (25, 0, -10), (25, 0, 10), (-2, 0, 10)],
          fill=(34, 139, 34), outline=(20, 100, 20), width=2)
    
    # Hole
    hole_pts = []
    for i in range(24):
        t = 2 * math.pi * i / 24
        hole_pts.append((HOLE_R * math.cos(t), 0.005, HOLE_R * math.sin(t)))
    poly3(screen, cam, hole_pts, fill=(10, 10, 10), outline=(0, 0, 0), width=1)
    
    # Flagstick
    line3(screen, cam, (0, 0, 0), (0, 1.5, 0), (200, 200, 200), 3)
    # Flag
    flag_pts = [(0, 1.5, 0), (0, 1.5, 0.4), (0, 1.3, 0.4), (0, 1.3, 0)]
    poly3(screen, cam, flag_pts, fill=(255, 50, 50), outline=(200, 0, 0), width=1)
    
    # Optimal distance marker (arc)
    if optimal_d is not None:
        prev = None
        for i in range(41):
            t = -math.pi/2 + math.pi * i / 40
            p = (optimal_d * math.cos(t), 0.01, optimal_d * math.sin(t))
            pr = cam.project(p)
            if pr and prev: 
                pygame.draw.line(screen, (255, 255, 0), prev[:2], pr[:2], 3)
            prev = pr

def draw_ball(screen, cam, pos, color):
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
        if prev is not None: pygame.draw.line(screen, color, prev, (int(pr[0]), int(pr[1])), 2)
        prev = (int(pr[0]), int(pr[1]))

def draw_shooter(screen, cam, d):
    base = (d, 0, 0)
    head = (d, 1.7, 0)
    hand = (d, 0.9, 0)
    
    line3(screen, cam, base, (d, 1.0, 0), (30, 60, 150), 6)
    pr = cam.project(head)
    if pr:
        rr = max(4, int(cam.radius(head, 0.10) or 4))
        pygame.draw.circle(screen, (255, 220, 180), (int(pr[0]), int(pr[1])), rr)
    line3(screen, cam, (d, 1.0, 0), hand, (30, 60, 150), 5)
    line3(screen, cam, hand, (d - 0.2, 0.1, 0), (150, 150, 150), 3)
    
    pr2 = cam.project((d, BALL_R, 0))
    if pr2: 
        pygame.draw.circle(screen, (255, 255, 255), (int(pr2[0]), int(pr2[1])), max(2, int(cam.radius((d, BALL_R, 0), BALL_R) or 2)))


# =====================================================================
#  MAIN
# =====================================================================
def main():
    global throws, makes, total_miss, cal_attempts, cal_makes

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("3D Golf AI — ULTRA-FAST PUTT/CHIP OPTIMISATION")
    clock = pygame.time.Clock()

    try:
        f_big = pygame.font.SysFont("consolas,couriernew,monospace", 22, bold=True)
        f     = pygame.font.SysFont("consolas,couriernew,monospace", 18, bold=True)
        f_s   = pygame.font.SysFont("consolas,couriernew,monospace", 14)
    except Exception:
        f_big = pygame.font.Font(None, 26)
        f     = pygame.font.Font(None, 22)
        f_s   = pygame.font.Font(None, 16)

    cam = Camera((15.0, 8.0, 15.0), (5.0, 0.0, 0.0), fov=62)

    loaded = load_brain()
    if not loaded:
        pretrain_brain() 
    else:
        print("loaded existing brain")

    state, cur_d, cur_pts, cur_idx, cur_made = "ready", 8.0, [], 0.0, False
    cur_action, last_pred, last_act, last_hit, last_value = (0.0, 8.0), 0.0, (0.0, 8.0), "", 0.0
    turbo, paused, speed_mult, mode, fixed_d = False, False, 1.0, 0, 8.0
    recent, TURBO_N = deque(maxlen=100), 20

    def do_throw(d=None, th=None, sv=None, greedy=False):
        nonlocal last_pred, last_act, last_hit, last_value
        global throws, makes, total_miss, cal_attempts, cal_makes

        if d is None:
            if mode == 2:
                opt = get_optimal()
                if opt is not None:
                    d, th, sv = opt[0], opt[1], opt[2]
                    greedy = True
                else:
                    d = float(rng.uniform(D_MIN, D_MAX))
            elif mode == 1:
                d = fixed_d
            else:
                d = float(rng.uniform(D_MIN, D_MAX))

        if th is None or sv is None:
            th, sv = choose_action(d, greedy=greedy)

        pts, min_d, made = simulate(d, th, sv)
        add_sample(d, th, sv, min_d)
        
        k = 5 if throws < 500 else 2
        batch = 256 if throws < 500 else 128
        train_steps(k=k, batch=batch)

        pn = float(net.forward(np.array([[norm_d(d), norm_a(th), norm_s(sv)]]))[0, 0])
        pred_miss = pn * TARGET_CAP

        throws += 1
        total_miss += min_d
        if made:
            makes += 1
            bin_makes[bin_idx(d)] += 1
        bin_attempts[bin_idx(d)] += 1

        bi = cal_bin_index(pred_miss)
        cal_attempts[bi] += 1.0
        if made: cal_makes[bi] += 1.0
        recent.append(1 if made else 0)

        last_act, last_value, last_pred = (th, sv), min_d, pn
        last_hit = "IN!" if made else ("FAR" if min_d > 2.0 else "CLOSE" if min_d < 0.5 else "MID")

        if throws % 100 == 0:
            save_brain()
            cal_attempts *= 0.7
            cal_makes *= 0.7
            print(f"  [{throws:5d} strokes | {makes} makes | "
                  f"{total_miss/throws:.2f}m avg miss | {100.0*makes/throws:5.1f}%] saved")

        return d, th, sv, pts, min_d, made

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
                fixed_d = float(np.clip(D_MIN + frac * (D_MAX - D_MIN), D_MIN, D_MAX))
                mode = 1
                state = "ready"

        if not paused:
            if turbo:
                for _ in range(TURBO_N):
                    d, th, sv, pts, md, made = do_throw()
                cur_d, cur_pts, cur_made = d, pts, made
                cur_idx = len(pts) - 1
                state = "ready"
            elif state == "ready":
                d, th, sv, pts, md, made = do_throw()
                cur_d, cur_pts, cur_made = d, pts, made
                cur_action = (th, sv)
                cur_idx = 0.0
                state = "flying"
            elif state == "flying":
                cur_idx += dt_real * speed_mult / DT
                if cur_idx >= len(cur_pts) - 1:
                    cur_idx = float(len(cur_pts) - 1)
                    state = "ready"

        opt = get_optimal()

        screen.fill((12, 24, 48))
        for y in range(0, 340, 4):
            c = int(18 + 30 * (y / 340))
            pygame.draw.rect(screen, (c // 2, c // 2 + 4, c + 20), (0, y, W, 4))

        draw_green(screen, cam, optimal_d=(opt[0] if opt else None))
        draw_ball(screen, cam, (0, 0.005, 0), (10, 10, 10))  # Hole shadow/detail

        if cur_pts and cur_idx > 0:
            col = (110, 235, 140) if cur_made else (255, 165, 70)
            draw_trail(screen, cam, cur_pts, cur_idx, col)
        if cur_pts:
            i = min(int(cur_idx), len(cur_pts) - 1)
            col = (110, 235, 140) if cur_made else (255, 165, 70)
            draw_ball(screen, cam, cur_pts[i], col)
        draw_shooter(screen, cam, cur_d)

        pct = (100.0 * makes / throws) if throws else 0.0
        last100 = (sum(recent) / len(recent)) if len(recent) == 100 else None
        last100s = f"{100.0*last100:5.1f}%" if last100 is not None else "  --  "
        mode_names = ["AUTO (directed)", "FIXED", "OPTIMAL"]
        mode_cols  = [(200, 215, 240), (200, 215, 240), (255, 215, 100)]

        panel = pygame.Surface((380, 360), pygame.SRCALPHA)
        panel.fill((8, 16, 32, 210))
        screen.blit(panel, (16, 16))
        pygame.draw.rect(screen, (70, 130, 90), pygame.Rect(16, 16, 380, 360), 2)

        y = 24
        screen.blit(f_big.render("3D GOLF AI", True, (245, 255, 245)), (28, y)); y += 30
        rows = [
            ("STROKES", f"{throws:>8d}"), ("MAKES", f"{makes:>8d}  ({pct:4.1f}%)"),
            ("AVG MISS", f"{(total_miss/max(1,throws)):>8.2f} m"), ("MAKE % (100)", f"{last100s:>8}"),
            ("CUR DIST", f"{cur_d:>8.2f} m"), ("CUR ANGLE", f"{last_act[0]:>8.1f} deg"),
            ("CUR SPEED", f"{last_act[1]:>8.2f} m/s"),
        ]
        for k, v in rows:
            screen.blit(f.render(f"{k:<14}{v}", True, (200, 235, 210)), (28, y)); y += 22

        y += 4
        screen.blit(f.render(f"MODE: {mode_names[mode]}", True, mode_cols[mode]), (28, y)); y += 26

        screen.blit(f.render("BEST (dist, angle, speed) FOR MAKE:", True, (255, 220, 180)), (28, y)); y += 22
        if opt is not None:
            d_, a_, s_, ep_, pm_, pm2_ = opt
            screen.blit(f.render(f"  dist = {d_:5.2f} m", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  angle = {a_:5.1f} deg", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  speed = {s_:5.2f} m/s", True, (255, 255, 255)), (28, y)); y += 20
            screen.blit(f.render(f"  P(make) = {pm_:5.3f}", True, (200, 255, 200)), (28, y)); y += 20
            screen.blit(f.render(f"  Expected Make = {ep_:5.3f}", True, (120, 255, 150)), (28, y)); y += 20
            screen.blit(f_s.render(f"  (net pred miss {pm2_:.3f} m)", True, (160, 200, 180)), (28, y))
        else:
            screen.blit(f.render("  gathering data...", True, (200, 180, 120)), (28, y))

        if paused: badge, bcol = "PAUSED", (240, 200, 80)
        elif turbo: badge, bcol = "TURBO", (255, 130, 70)
        elif throws < 120: badge, bcol = "PRE-TRAINED", (110, 235, 150)
        elif epsilon() > 0.15: badge, bcol = "LEARNING", (110, 190, 255)
        else: badge, bcol = "FINE-TUNING", (110, 235, 150)
        
        bw = f.render(badge, True, (12, 14, 22))
        pad = 12
        rect = pygame.Rect(W - 28 - bw.get_width() - 2*pad, 20, bw.get_width() + 2*pad, 34)
        pygame.draw.rect(screen, bcol, rect, border_radius=8)
        screen.blit(bw, (rect.x + pad, rect.y + 7))
        
        if last_hit:
            col = (100, 255, 100) if last_hit == "IN!" else (255, 200, 120)
            screen.blit(f.render(last_hit, True, col), (W - 100, 68))

        help_txt = "SPACE pause  T turbo  A mode  C wipe  1-5 speed  click=aim  ESC quit"
        screen.blit(f_s.render(help_txt, True, (140, 175, 160)), (16, H - 26))
        screen.blit(f_s.render(f"brain: {os.path.basename(SAVE_PATH)}", True, (120, 155, 145)), (16, H - 46))

        pygame.display.flip()

    save_brain()
    pygame.quit()
    print(f"\nfinal: {throws} strokes | {makes} makes "
          f"({100.0*makes/max(1,throws):.1f}%) | {total_miss/max(1,throws):.2f}m avg miss")
    print("brain saved to", SAVE_PATH)


if __name__ == "__main__":
    main()