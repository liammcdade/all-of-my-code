import random
from collections import defaultdict
import math

# Import the real functions directly from the module
import importlib.util, pathlib

# Load the module without running the main guard
spec = importlib.util.spec_from_file_location(
    "euro2028",
    pathlib.Path("sportsanalysis/euro/euro2028_playoffs_sim.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

all_teams_f = mod.all_teams
elo_ranking_f = mod.elo_ranking
hosts_f = ["England", "Republic of Ireland", "Scotland", "Wales", "Northern Ireland"]
GRAND_TOTAL_DIRECT = 16

for seed in range(10_000):
    random.seed(seed)

    # Build groups using real simulation function
    remaining_pool = [t for t in all_teams_f if t not in hosts_f]
    remaining_pool.append(hosts_f[4])
    random.shuffle(remaining_pool)
    groups = [[] for _ in range(12)]
    assigned_hosts = hosts_f[:4]
    for i, host in enumerate(assigned_hosts):
        groups[i].append(host)
    groups[0].extend(remaining_pool[0:4])
    groups[1].extend(remaining_pool[4:8])
    groups[2].extend(remaining_pool[8:11])
    groups[3].extend(remaining_pool[11:14])
    idx=14
    for i in range(4,12):
        groups[i].extend(remaining_pool[idx:idx+4])
        idx+=4

    # Run group stages
    winners, runners_up, stats = [], [], {}
    for g in groups:
        s, gs = mod.simulate_group_stage(g)
        winners.append(s[0]); runners_up.append(s[1]); stats.update(gs)

    def ruk(team):
        mp = stats[team]['mp']; ppg = stats[team]['points']/mp
        return(-ppg, -(stats[team]['gf']-stats[team]['ga'])/mp, -stats[team]['gf']/mp)

    rus_s = sorted(runners_up, key=ruk)
    brus = rus_s[:8]; wrus = rus_s[8:]

    hw = [w for w in winners[:4] if w in hosts_f]
    nh = max(0, 4-len(hw))
    uh = [h for h in hosts_f[:4] if h not in hw]
    hs = sorted(uh, key=ruk)[:nh]
    nhu = [r for r in brus if r not in hosts_f]
    nhu_slots = max(0, 8-nh)
    nhu_used = nhu[:nhu_slots]
    dq = (set(winners) | {r for r in brus if r in hosts_f} | set(hs) | set(nhu_used))

    if len(dq) > 16:
        print(f"SEED {seed}: OVERFLOW! {len(dq)} direct candidates")
        print(f"  winners={winners}")
        print(f"  hw={hw}, nh={nh}, hs={hs}")
        print(f"  brus={brus}")
        print(f"  hr_in_brus={[r for r in brus if r in hosts_f]}")
        print(f"  nhu_used={nhu_used}, nhu_slots={nhu_slots}")
        print(f"  dq={sorted(dq)}")
        break
else:
    print(f"No overflow in {10_000} seeds")
