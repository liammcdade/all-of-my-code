import math


class CalculatorProcessor:
    """Scientific calculator with unit conversion capabilities."""
    
    def sin(self, value: float) -> float:
        """Calculate sine of value (in radians)."""
        return math.sin(value)

    def cos(self, value: float) -> float:
        """Calculate cosine of value (in radians)."""
        return math.cos(value)

    def tan(self, value: float) -> float:
        """Calculate tangent of value (in radians)."""
        return math.tan(value)

    def log(self, value: float, base: float = None) -> float:
        """Calculate logarithm. Natural log if base is None."""
        if value <= 0:
            raise ValueError("Logarithm input must be positive")
        if base is None:
            return math.log(value)
        if base <= 0 or base == 1:
            raise ValueError("Logarithm base must be positive and not equal to 1")
        return math.log(value, base)

    def sqrt(self, value: float) -> float:
        """Calculate square root of value."""
        if value < 0:
            raise ValueError("Square root input must be non-negative")
        return math.sqrt(value)

    def convert_unit(self, value: float, from_unit: str, to_unit: str, category: str) -> float:
        """Convert value between units within a category."""
        if category == "temperature":
            # Convert to Celsius first
            if from_unit == "F":
                celsius = (value - 32) * 5/9
            elif from_unit == "K":
                celsius = value - 273.15
            elif from_unit == "C":
                celsius = value
            else:
                raise ValueError(f"Unknown temperature unit: {from_unit}")

            # Convert from Celsius to target
            if to_unit == "F":
                return (celsius * 9/5) + 32
            elif to_unit == "K":
                return celsius + 273.15
            elif to_unit == "C":
                return celsius
            else:
                raise ValueError(f"Unknown temperature unit: {to_unit}")

        # Length and weight conversions
        conversions = {
            "length": {"m": 1.0, "km": 1000.0, "ft": 0.3048, "mile": 1609.34},
            "weight": {"kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
        }

        if category not in conversions:
            raise ValueError(f"Unknown category: {category}")

        units = conversions[category]
        if from_unit not in units or to_unit not in units:
            raise ValueError(f"Unknown units in {category}: {from_unit}, {to_unit}")

        # Convert via base unit
        base_value = value * units[from_unit]
        return base_value / units[to_unit]


