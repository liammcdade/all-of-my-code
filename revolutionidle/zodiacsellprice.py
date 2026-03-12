def calculate_zodiac_sale_price(zodiac_rarity, zodiac_quality, zodiac_level):
    """
    Calculate the Zodiac Sale Price based on the given formula.
    
    Parameters:
    zodiac_rarity (float or int): The rarity of the zodiac.
    zodiac_quality (float or int): The quality of the zodiac.
    zodiac_level (float or int): The level of the zodiac.
    
    Returns:
    float: The calculated sale price.
    """
    # Conditional multiplier for rarity < 8
    rarity_mult = 2 if zodiac_rarity < 8 else 1
    
    # Conditional multiplier for level >= 100
    level_mult = ((zodiac_level - 90) / 10) ** 2.5 if zodiac_level >= 100 else 1
    
    # Inner calculation
    inner = (
        (1.125) *
        zodiac_quality *
        (9 + zodiac_level ** 2) *
        rarity_mult *
        level_mult
    ) / 10
    
    # Final price
    price = inner ** 0.75 * (1.1 ** zodiac_rarity)
    
    return price

# List to store results: each entry is a tuple (rarity, quality, level, price)
results = []

print("Zodiac Sale Price Calculator")
print("Enter values for rarity, quality, and level. Type 'done' when finished to see the highest selling one.")

while True:
    rarity_input = input("Enter Zodiac Rarity (or 'done' to finish): ").strip()
    if rarity_input.lower() == 'done':
        break
    
    try:
        zodiac_rarity = float(rarity_input)
        zodiac_quality = float(input("Enter Zodiac Quality: ").strip())
        zodiac_level = float(input("Enter Zodiac Level: ").strip())
        
        price = calculate_zodiac_sale_price(zodiac_rarity, zodiac_quality, zodiac_level)
        print(f"Calculated Sale Price: {price:.2f}")
        
        results.append((zodiac_rarity, zodiac_quality, zodiac_level, price))
    except ValueError:
        print("Invalid input. Please enter numeric values.")

if results:
    # Find the one with the maximum price
    max_result = max(results, key=lambda x: x[3])
    print("\nThe highest selling Zodiac:")
    print(f"Rarity: {max_result[0]}, Quality: {max_result[1]}, Level: {max_result[2]}, Price: {max_result[3]:.2f}")
else:
    print("No calculations performed.")