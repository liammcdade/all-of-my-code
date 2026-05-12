import random
from collections import defaultdict
from tqdm import tqdm

# =========================
# FULL PLAYER RATINGS
# =========================
ratings = {
    "Judd Trump": 2827.5,
    "Zhao Xintong": 2791.1,
    "Mark Selby": 2789.6,
    "Ronnie O'Sullivan": 2756.8,
    "John Higgins": 2746.7,
    "Kyren Wilson": 2737.6,
    "Shaun Murphy": 2743.3,
    "Mark J Williams": 2723.2,
    "Wu Yize": 2735.4,
    "Neil Robertson": 2711.5,
    "Mark Allen": 2707.3,
    "Barry Hawkins": 2706.3,
    "Xiao Guodong": 2695.4,
    "Ding Junhui": 2689.3,
    "Ali Carter": 2672.4,
    "Zhou Yuelong": 2666.8,
    "Jak Jones": 2666.5,
    "Zhang Anda": 2656.5,
    "Gary Wilson": 2640.2,
    "Elliot Slessor": 2639.4,
    "Thepchaiya Un-Nooh": 2638.7,
    "Si Jiahui": 2636.0,
    "Stuart Bingham": 2632.9,
    "Jack Lisowski": 2632.6,
    "Chris Wakelin": 2632.3,
    "Joe O'Connor": 2630.3,
    "Chang Bingyu": 2624.1,
    "Hossein Vafaei": 2621.9,
    "Vinnie Calabrese (a)": 2613.6,
    "David Gilbert": 2610.6,
    "Luca Brecel": 2608.4,
    "Pang Junxu": 2605.0,
    "Fan Zhengyi": 2602.2,
    "Yuan Sijun": 2600.1,
    "Jiang Jun": 2598.3,
    "Stan Moody": 2597.5,
    "Liam Highfield": 2593.0,
    "Stephen Maguire": 2591.3,
    "Anthony McGill": 2580.8,
    "Matthew Selt": 2575.8,
    "Ricky Walden": 2575.3,
    "Marco Fu": 2575.1,
    "Lei Peifan": 2572.9,
    "Zak Surety": 2571.0,
    "Scott Donaldson": 2567.4,
    "Ashley Hugill (a)": 2564.0,
    "Sam Craigie": 2561.9,
    "Aaron Hill": 2561.6,
    "Igor Figueiredo (a)": 2561.1,
    "Ben Woollaston": 2559.4,
    "Xu Si": 2555.9,
    "Jackson Page": 2554.9,
    "Tom Ford": 2553.8,
    "Jimmy Robertson": 2548.9,
    "Ryan Day": 2547.9,
    "He Guoqiang": 2546.3,
    "Matthew Stevens": 2546.1,
    "Daniel Wells": 2542.6,
    "Noppon Saengkham": 2539.3,
    "Liu Hongyu": 2536.4,
    "Liam Pullen": 2536.0,
    "Jamie Clarke (a)": 2534.4,
    "Oliver Lines": 2532.8,
    "Louis Heathcote": 2531.2,
    "Graeme Dott": 2526.6,
    "Michael Holt": 2523.0,
    "Robbie Williams": 2521.8,
    "Long Zehuang": 2519.0,
    "Julien Leclercq": 2516.1,
    "Ben Mertens": 2509.7,
    "Martin O'Donnell": 2507.0,
    "George Pragnell (a)": 2500.8,
    "Joe Perry (a)": 2498.0,
    "Sunny Akani": 2494.5,
    "Dylan Emery": 2494.5,
    "Mark Davis": 2492.3,
    "Gao Yang": 2491.2,
    "Jamie Jones": 2491.2,
    "Mark Joyce (a)": 2490.0,
    "Lyu Haotian": 2490.0,
    "Ian Burns": 2489.1,
    "Hammad Miah (a)": 2482.6,
    "David Grace": 2481.0,
    "Antoni Kowalski": 2477.5,
    "Craig Steadman (a)": 2475.5,
    "Artemijs Zizins": 2474.9,
    "Peter Lines (a)": 2470.3,
    "Robert Milkins": 2469.5,
    "David Lilley": 2469.4,
    "Stuart Carrington (a)": 2469.0,
    "Ishpreet Singh Chadha": 2467.1,
    "Ali Gharahgozlou (a)": 2460.7,
    "Rory Thor (a)": 2458.1,
    "Steven Hallworth": 2458.0,
    "John Astley (a)": 2452.6,
    "Ashley Carty (a)": 2452.2,
    "Iulian Boiko": 2451.6,
    "Bulcsu Revesz": 2451.5,
    "Alfie Burden (a)": 2447.6,
    "Liam Davies": 2445.3,
    "Wang Yuchen": 2439.6,
    "Ryan Thomerson (a)": 2436.3,
    "Hassan Kerde (a)": 2436.2,
    "Patrick Whelan (a)": 2436.1,
    "Ma Hailong (a)": 2435.3,
    "Dominic Dale (a)": 2433.1,
    "Oliver Sykes (a)": 2432.6,
    "Alexander Ursenbacher": 2431.9,
    "Ross Muir": 2429.3,
    "Tian Pengfei (a)": 2427.3,
    "Xing Zihao (a)": 2423.7,
    "Duane Jones": 2422.0,
    "Anthony Hamilton (a)": 2421.0,
    "Jordan Brown": 2420.9,
    "Alfie Davies (a)": 2419.3,
    "Shaun Dalitz (a)": 2418.6,
    "Steve Mifsud (a)": 2417.0,
    "Cheung Ka Wai": 2409.9,
    "Paul Norris (a)": 2408.2,
    "Allan Taylor": 2406.2,
    "Wang Xinbo (a)": 2400.7,
    "Luo Honghao (a)": 2400.6,
    "Peter Devlin (a)": 2398.1,
    "Ehsan Heydari Nezhad (a)": 2395.3,
    "Simon Blackwell (a)": 2394.7,
    "Harvey Chandler (a)": 2393.4,
    "Barry Pinches (a)": 2393.2,
    "Nattanapong Chaikul (a)": 2389.9,
    "Florian Nussle": 2389.0,
    "Andrew Higginson (a)": 2387.2,
    "Mitchell Mann": 2384.5,
    "Ali Jaleel (a)": 2381.9,
    "Joseph Conchie (a)": 2381.3,
    "Yao Pengcheng": 2380.0,
    "Lan Yuhao": 2379.9,
    "Umut Dikme (a)": 2379.2,
    "Ryan Davies (a)": 2377.1,
    "Sean O'Sullivan (a)": 2376.6,
    "Mateusz Baranowski": 2375.6,
    "James Cahill (a)": 2372.3,
    "Zack Richardson (a)": 2371.0,
    "Siyavosh Mozayani (a)": 2365.2,
    "Alex Clenshaw (a)": 2363.8,
    "Lawrence Millington (a)": 2363.5,
    "Robbie McGuigan": 2362.1,
    "Sanderson Lam": 2360.1,
    "Fung Kwok Wai (a)": 2357.1,
    "Antony Parsons (a)": 2353.7,
    "Mohammed Shehab": 2353.7,
    "Gerard Greene (a)": 2353.6,
    "Zhao Hanyang": 2352.3,
    "Farakh Ajaib": 2351.9,
    "Xu Yichen": 2351.5,
    "Billy Castle (a)": 2348.7,
    "Mark Lloyd (a)": 2348.4,
    "Peng Yisong (a)": 2347.8,
    "Simon Bedford (a)": 2344.7,
    "Kuldesh Johal (a)": 2341.2,
    "Haydon Pinhey": 2340.2,
    "Adrian Law (a)": 2339.9,
    "Amir Sarkhosh": 2339.7,
    "William Lemons (a)": 2337.6,
    "Cody Turner (a)": 2336.8,
    "Cale Barrett (a)": 2335.3,
    "Mark Canovan (a)": 2334.6,
    "Gong Chenzhi": 2334.3,
    "Claudio Menechini (a)": 2331.6,
    "Luke Pinches (a)": 2330.2,
    "David Wright (a)": 2329.5,
    "Matthew Scarborough (a)": 2328.1,
    "Liu Wenwei": 2325.9,
    "Alex Millington (a)": 2325.3,
    "Lomnaw Ayuttaya (a)": 2324.7,
    "Wan Sin Man Nansen (a)": 2323.5,
    "Ali Ali (a)": 2320.4,
    "Andres Petrov (a)": 2319.4,
    "Mykhailo Larkov (a)": 2318.5,
    "Xavier Daw (a)": 2318.4,
    "Luo Zetao (a)": 2318.1,
    "Ali Al Obaidly (a)": 2314.5,
    "Jenson Kendrick (a)": 2312.8,
    "Nicolas Mortreux (a)": 2310.8,
    "Dean Young (a)": 2310.6,
    "Andrew Pagett (a)": 2310.0,
    "Ismail Turker (a)": 2309.1,
    "Chau Hon Man (a)": 2308.8,
    "Chen Qi'en (a)": 2308.7,
    "Sean Maddocks (a)": 2308.0,
    "Roger Farebrother (a)": 2307.0,
    "Adrian Ridley (a)": 2306.5,
    "Rory McLeod (a)": 2305.6,
    "Ken Doherty": 2305.5,
    "Lim Kok Leong": 2304.9,
    "Chang Yu Kiu (a)": 2304.9,
    "Dale Kwok (a)": 2303.8,
    "Brian Ochoiski (a)": 2299.4,
    "Jimmy White": 2297.8,
    "Riley Powell (a)": 2297.7,
    "Habib Subah Humood (a)": 2297.3,
    "Zhou Jinhao (a)": 2295.3,
    "Huang Jiahao": 2294.5,
    "Emad Adnan (a)": 2292.8,
    "Aaron Busuttil (a)": 2291.5,
    "James Mifsud (a)": 2290.7,
    "Daniel Womersley (a)": 2290.3,
    "Alan McCarthy (a)": 2287.7,
    "Jack Bradford (a)": 2286.2,
    "Oliver Brown": 2285.8,
    "Lee Daegyu (a)": 2284.1,
    "Ian Martin (a)": 2284.1,
    "Callum Beresford (a)": 2282.4,
    "Hassan Abdalla (a)": 2281.8,
    "Chris Totten": 2281.5,
    "Jamie O'Neill (a)": 2279.7,
    "Bai Yulu": 2278.3,
    "Matthew Glasby (a)": 2277.7,
    "Denys Khmelevskyi (a)": 2277.3,
    "Liu Yang (a)": 2276.0,
    "Mostafa Dorgham (a)": 2275.8,
    "Joshua Thomond (a)": 2275.0,
    "Babar Masih (a)": 2274.9,
    "Khalid Ali Alkamali (a)": 2274.6,
    "Michal Szubarczyk": 2272.0,
    "Liam Graham": 2272.0,
    "Daniell Haenga (a)": 2271.7,
    "Anton Kazakov (a)": 2271.5,
    "Robert Read (a)": 2270.7,
    "Shaun Liu (a)": 2269.2,
    "Haris Tahir": 2265.9,
    "Omar Amer (a)": 2264.7,
    "Yeung Chi Kin (a)": 2262.3,
    "Liu Linhao (a)": 2262.1,
    "Narongdat Takantong (a)": 2261.5,
    "Putthakarn Kimsuk (a)": 2259.5,
    "Ritthichai Chimphanang (a)": 2259.2,
    "Gary Thomson (a)": 2259.2,
    "Kayden Brierley (a)": 2258.2,
    "Asutosh Padhy (a)": 2257.1,
    "Jack Borwick (a)": 2257.1,
    "Rodion Judin (a)": 2256.5,
    "Amin Sanjael (a)": 2255.6,
    "Paul Deaville (a)": 2255.6,
    "Jayden Dinga (a)": 2255.3,
    "Leone Crowley": 2252.6,
    "Sean Dempsey (a)": 2251.1,
    "Liang Xiaolong (a)": 2248.8,
    "Karar Najim (a)": 2248.6,
    "Hesham Alsaqer (a)": 2243.7,
    "Hayden Staniland (a)": 2240.3,
    "Sybren Sokolowski (a)": 2238.6,
    "Max Handley (a)": 2236.1,
    "Riley Parsons (a)": 2235.5,
    "M Phetmalaikul (a)": 2235.0,
    "Hamim Hussain (a)": 2234.1,
    "Nathan Jones (a)": 2233.7,
    "Connor Benzey": 2233.0,
    "Joel Connolly (a)": 2229.7,
    "Jake Crofts (a)": 2229.4,
    "Digvijay Kadian (a)": 2228.2,
    "Neal Jones (a)": 2227.4,
    "Daan Leyssen (a)": 2226.2,
    "Sahil Nayyar": 2223.2,
    "Chatchapong Nasa": 2221.6,
    "Brett Watson (a)": 2220.9,
    "Ong Jia Jun Jaden (a)": 2220.1,
    "Zhang Zhijie (a)": 2216.7,
    "Filips Kalnins (a)": 2216.5,
    "Saqib Nasir (a)": 2212.8,
    "Lewis Ullah (a)": 2212.3,
    "Vladislav Gradinari (a)": 2208.9,
    "Sean McAllister (a)": 2205.5,
    "Aidan Murphy (a)": 2203.2,
    "Krzysztof Czapnik (a)": 2202.9,
    "Oliver Briffett-Payne (a)": 2202.9,
    "Fergal Quinn": 2200.0,
    "Halim Hussain (a)": 2199.7,
    "Manuel Ederer (a)": 2196.4,
    "Mark Vincent (a)": 2184.3,
    "Jessica Woods (a)": 2181.9,
    "Nikita Bazilevics (a)": 2181.9,
    "Matt Williams (a)": 2181.9,
    "Phil O'Kane (a)": 2181.7,
    "Christian Richter (a)": 2179.0,
    "Chris Kerr (a)": 2175.2,
    "Ziyad Alqabbani (a)": 2173.0,
    "Faizaan Mohammed (a)": 2168.4,
    "Daniel Boyes (a)": 2164.2,
    "Joshua Cooper (a)": 2163.8,
    "Josh Mulholland (a)": 2163.4,
    "Jason Tart (a)": 2163.3,
    "Anthony Wall (a)": 2161.1,
    "Aidan Gallagher (a)": 2161.1,
    "Stuart Watson (a)": 2160.7,
    "Brandon Hall (a)": 2159.5,
    "Alex Render (a)": 2157.9,
    "Mahmoud El Hareedy (a)": 2154.1,
    "Mark Bell (a)": 2146.9,
    "Velian Dimitrov (a)": 2144.2,
    "Stephen Kershaw (a)": 2143.8,
    "Kreishh Gurbaxani": 2143.0,
    "Arsenii Korolev (a)": 2142.8,
    "Lee Shanker (a)": 2141.4,
    "Kaylan Patel (a)": 2140.7,
    "Ng On Yee": 2134.3,
    "Peter Quinlivan (a)": 2131.2,
    "Andrew Siddons (a)": 2128.6,
    "Steve Jay (a)": 2122.8,
    "Jay Bullen (a)": 2115.9,
    "Joseph Casha (a)": 2106.8,
    "Nigel Clarke (a)": 2105.5,
    "Edward Jones (a)": 2095.9,
    "Dylan Smith (a)": 2091.2,
    "Reanne Evans": 2091.2,
    "Michal Kotiuk (a)": 2089.3,
    "Hatem Yassen": 2083.1,
    "Fathey Refai (a)": 2080.5,
    "Steven Wardropper (a)": 2075.1,
    "Elias Martin-Beris (a)": 2073.7,
    "Kian Dennett (a)": 2067.7,
    "Victor Sarkis (a)": 2055.6,
    "Adam Abbas (a)": 2048.4,
    "Brandon Nguyen (a)": 2026.0,
    "Mink Nutcharut": 1986.9,
    "Jonas Luz": 1967.4,
    "Ahmed Aly Elsayed (a)": 1965.2,
    "Baipat Siripaporn (a)": 1946.6,
}

# =========================
# WIN PROBABILITY
# =========================
def win_prob(p1, p2):
    return 1 / (1 + 10 ** ((ratings[p2] - ratings[p1]) / 400))


# =========================
# MATCH SIMULATION
# =========================
def simulate_match(p1, p2, best_of):
    target = best_of // 2 + 1
    s1 = s2 = 0
    p = win_prob(p1, p2)

    while s1 < target and s2 < target:
        if random.random() < p:
            s1 += 1
        else:
            s2 += 1

    return p1 if s1 > s2 else p2


# =========================
# CURRENT ROUND 1 STATE
# =========================
round1 = [
    ("Zhao Xintong", "Ding Junhui"),        # already determined winners feeding R2
    ("Xiao Guodong", "Shaun Murphy"),      # Murphy vs Fan still to play → handled below
    ("John Higgins", "Ronnie O'Sullivan"),
    ("Chris Wakelin", "Neil Robertson"),
    ("Kyren Wilson", "Mark Allen"),
    ("Barry Hawkins", "Mark J Williams"),
    ("Mark Selby", "Wu Yize"),
    ("Si Jiahui", "Judd Trump"),
]

# Note: unresolved matches replaced dynamically

# =========================
# FULL SIMULATION FUNCTION
# =========================
def simulate_tournament():
    
    # --- ROUND 2 (build properly) ---
    r2 = []

    # 1
    r2.append(("Zhao Xintong", "Ding Junhui"))

    # 2 (Murphy vs Fan → completed, Murphy won)
    murphy = "Shaun Murphy"
    r2.append(("Xiao Guodong", murphy))

    # 3 (Ronnie vs He → completed, Ronnie won)
    ronnie = "Ronnie O'Sullivan"
    r2.append(("John Higgins", ronnie))

    # 4 (Wakelin vs Pullen → completed, Wakelin won; Robertson vs Pang → pending)
    wakelin = "Chris Wakelin"
    robertson = simulate_match("Neil Robertson", "Pang Junxu", 19)
    r2.append((wakelin, robertson))

    # 5 (Wilson vs Moody → completed, Wilson won)
    wilson = "Kyren Wilson"
    r2.append((wilson, "Mark Allen"))

    # 6
    r2.append(("Barry Hawkins", "Mark J Williams"))

    # 7
    selby = simulate_match("Mark Selby", "Jak Jones", 19)
    wu = "Wu Yize"
    r2.append((selby, wu))

    # 8
    si = simulate_match("Si Jiahui", "Hossein Vafaei", 19)
    trump = "Judd Trump"
    r2.append((si, trump))

    # --- ROUND 2 SIM ---
    qf_players = [simulate_match(a, b, 25) for a, b in r2]

    # --- QUARTERS ---
    qf = [(qf_players[i], qf_players[i+1]) for i in range(0, 8, 2)]
    sf_players = [simulate_match(a, b, 25) for a, b in qf]

    # --- SEMIS ---
    sf = [(sf_players[0], sf_players[1]), (sf_players[2], sf_players[3])]
    finalists = [simulate_match(a, b, 33) for a, b in sf]

    # --- FINAL ---
    # Wu Yize vs Shaun Murphy
    finalists = ["Wu Yize", "Shaun Murphy"]
    # Current score: Wu Yize 13 - Shaun Murphy 12, first to 18
    p1 = "Wu Yize"
    p2 = "Shaun Murphy"
    target = 18
    s1 = 13  # Wu Yize
    s2 = 12   # Shaun Murphy
    p = win_prob(p1, p2)
    while s1 < target and s2 < target:
        if random.random() < p:
            s1 += 1
        else:
            s2 += 1
    champion = p1 if s1 > s2 else p2

    return champion


# =========================
# MONTE CARLO
# =========================
def run_sims(n=10000):
    results = defaultdict(int)

    for _ in tqdm(range(n)):
        winner = simulate_tournament()
        results[winner] += 1

    for k in results:
        results[k] = results[k] / n * 100

    return dict(sorted(results.items(), key=lambda x: -x[1]))


# =========================
# ANALYSIS FUNCTIONS
# =========================
def get_player_rating(player):
    return ratings.get(player, 0)

def get_average_rating(players):
    if not players:
        return 0
    return sum(get_player_rating(p) for p in players) / len(players)

def get_round1_winners():
    # From the known results (updated with completed matches)
    return ["Zhao Xintong", "Ding Junhui", "Xiao Guodong", "Shaun Murphy", "John Higgins", "Ronnie O'Sullivan", "Chris Wakelin", "Kyren Wilson", "Mark Allen", "Barry Hawkins", "Mark J Williams", "Wu Yize", "Judd Trump"]

def analyze_current_state():
    winners = get_round1_winners()
    avg_rating = get_average_rating(winners)
    print(f"Round 1 winners average rating: {avg_rating:.2f}")
    print("Winners and their ratings:")
    for w in winners:
        print(f"  {w}: {get_player_rating(w)}")

# =========================
# RUN SIMULATION AND ANALYSIS
# =========================
if __name__ == "__main__":
    print("=== Tournament Analysis ===")
    analyze_current_state()
    print("\n=== Monte Carlo Simulation Results ===")
    results = run_sims(10000)
    for player, prob in results.items():
        print(f"{player}: {prob:.2f}%")