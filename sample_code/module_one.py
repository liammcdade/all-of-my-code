# This is a module-level comment for module_one
class Greeter:
    """
    A simple class to greet people.
    It stores a greeting message.
    """
    # Class variable comment
    default_greeting = "Hello"

    def __init__(self, name):
        # Comment for __init__
        self.name = name  # Inline comment for name

    def greet(self, loud=False):
        """Greets the person."""
        message = f"{self.default_greeting}, {self.name}!"
        if loud:
            message = message.upper()
        print(message)
        return message


# Utility function for demonstration
def utility_function(verbose=True):
    """
    Utility function for module_one.
    Returns True if utility is working and prints a message.
    If verbose is False, does not print.
    """
    if verbose:
        print("Utility function called from module_one!")
    return True

another_var = 100
