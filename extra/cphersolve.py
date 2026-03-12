def first_year_without_leap(current_year: int, drift_threshold_days: float) -> int:
    tropical_year = 365.24219042
    gregorian_year = 365.2425
    annual_drift = gregorian_year - tropical_year

    years_until_drift = drift_threshold_days / annual_drift
    first_no_leap_year = int(current_year + years_until_drift)
    return first_no_leap_year


# Define variables before using them
current_year = 2025
drift_threshold = 1  # 1 day drift

year_to_skip_leap = first_year_without_leap(current_year, drift_threshold)
print(f"Leap years might start being skipped from year {year_to_skip_leap} onward.")

# Simple Caesar cipher utility
def caesar_cipher(text, shift):
    """Encodes/decodes text using a Caesar cipher with the given shift."""
    result = []
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result.append(chr((ord(char) - base + shift) % 26 + base))
        else:
            result.append(char)
    return ''.join(result)

# Example usage
if __name__ == "__main__":
    encoded = caesar_cipher("Hello World!", 3)
    print(f"Encoded: {encoded}")
    decoded = caesar_cipher(encoded, -3)
    print(f"Decoded: {decoded}")
