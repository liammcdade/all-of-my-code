import math
import sys
from tqdm import tqdm
import sys
sys.set_int_max_str_digits(0)   # 0 = no limit

def arctan_inv(x, S, target_digits, desc, position):
    """
    Compute S * arctan(1/x) with two progress bars:
      - terms processed
      - digits guessed so far (out of target_digits)
    """
    x2 = x * x
    digits_per_term = 2 * math.log10(x)          # ~log10(x^2) digits/term
    est_terms = int(target_digits / digits_per_term) + 10

    term = S // x                                # k = 0 term
    total = term
    k = 1
    guessed = int(math.log10(x))                 # digits from the first term

    with tqdm(total=est_terms,
              desc=f"{desc} terms",
              unit="t", position=position, leave=True,
              colour="cyan") as bar_terms, \
         tqdm(total=target_digits,
              desc=f"{desc} digits",
              unit="d", position=position + 1, leave=True,
              colour="green") as bar_digits:

        while term > 0:
            # term_k = term_{k-1} * (2k-1) / ((2k+1) * x^2)
            term = term * (2 * k - 1) // ((2 * k + 1) * x2)
            if k % 2 == 1:
                total -= term
            else:
                total += term
            k += 1
            bar_terms.update(1)

            new_guessed = min(int(digits_per_term * k), target_digits)
            if new_guessed > guessed:
                bar_digits.update(new_guessed - guessed)
                guessed = new_guessed

        # If we somehow overshoot, top up the digit bar
        if guessed < target_digits:
            bar_digits.update(target_digits - guessed)

    return total


def compute_pi(N, G=30):
    """
    Attempt pi to N decimals with Machin's formula.
    Returns the digit string (no decimal point).
    """
    S = 10 ** (N + G)
    approx_bytes = (N + G) // 9 * 4
    print(f"Scaling factor: S = 10^{N + G}")
    print(f"Each big integer is ~{approx_bytes/1e9:.2f} GB in memory\n")

    A5   = arctan_inv(5,   S, N, "arctan(1/5)",   position=0)
    A239 = arctan_inv(239, S, N, "arctan(1/239)", position=2)

    P = 16 * A5 - 4 * A239          # P = pi * 10^(N+G)
    pi_scaled = P // (10 ** G)      # pi * 10^N

    s = str(pi_scaled)
    if len(s) < N + 1:
        s = "0" * (N + 1 - len(s)) + s
    return s


if __name__ == "__main__":
    N = 100000

    print(f"Target: pi to {N:,} decimal places via Machin's formula.")
    print("This will NOT finish — Machin is ~O(N^2) big-int work, and")
    print("N = 10^9 means ~10^18 operations. Press Ctrl-C to stop.\n")

    try:
        pi_str = compute_pi(N)
        print(f"\npi = {pi_str[0]}.{pi_str[1:101]}...")
    except KeyboardInterrupt:
        print("\nInterrupted — no digits were verified.")
        sys.exit(0)