try:
    from module_one import Greeter, utility_function
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from module_one import Greeter, utility_function

# Using the Greeter class
my_greeter = Greeter("Alice")
my_greeter.greet()

# Using the utility function
if utility_function():
    print("Utility worked!")

# A variable that might be confused with another_var
another_variable = 200


def use_greeter_again(name, polite=False):
    """Uses Greeter again, possibly politely."""
    g = Greeter(name)
    if polite:
        g.default_greeting = "Good day"
    g.greet()

# New utility function for demonstration
def multiply_and_greet(name, number):
    """Greets and returns the number multiplied by 2."""
    g = Greeter(name)
    g.greet()
    result = number * 2
    print(f"{name}'s number doubled is {result}")
    return result

# Example usage
if __name__ == "__main__":
    use_greeter_again("Bob", polite=True)
    print(multiply_and_greet("Charlie", 21))
