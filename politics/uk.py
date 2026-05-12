parties = [
    "SNP",
    "Labour",
    "Conservative",
    "Reform",
    "Lib Dem",
    "Green"
]

# Constituency seats already won
constituency_seats = {
    "SNP": 55,
    "Labour": 3,
    "Conservative": 4,
    "Reform": 0,
    "Lib Dem": 6,
    "Green": 2
}

# Regional list votes
regional_votes = {
    "SNP": 232127,
    "Labour": 135209,
    "Conservative": 122379,
    "Reform": 139784,
    "Lib Dem": 99472,
    "Green": 125552
}


def allocate_ams_seats(
    parties,
    constituency_seats,
    regional_votes,
    seats_to_allocate=56
):
    """
    Scottish Parliament AMS / D'Hondt allocation
    """

    # Track regional seats won
    regional_seats = {party: 0 for party in parties}

    # Save allocation rounds
    rounds = []

    for round_number in range(1, seats_to_allocate + 1):

        scores = {}

        for party in parties:

            divisor = (
                constituency_seats[party]
                + regional_seats[party]
                + 1
            )

            score = regional_votes[party] / divisor

            scores[party] = score

        # Highest score wins seat
        winner = max(scores, key=scores.get)

        regional_seats[winner] += 1

        rounds.append({
            "round": round_number,
            "winner": winner,
            "scores": scores.copy()
        })

    return regional_seats, rounds


regional_seats, rounds = allocate_ams_seats(
    parties,
    constituency_seats,
    regional_votes,
    seats_to_allocate=56
)

# Final totals
print("FINAL RESULTS")
print("-" * 40)

for party in parties:

    constituency = constituency_seats[party]
    regional = regional_seats[party]
    total = constituency + regional

    print(
        f"{party:<15}"
        f" Constituency: {constituency:<3}"
        f" Regional: {regional:<3}"
        f" Total: {total}"
    )

print("\nFIRST 10 AMS ROUNDS")
print("-" * 40)

for r in rounds[:10]:

    print(
        f"Round {r['round']:>2} "
        f"Winner: {r['winner']}"
    )