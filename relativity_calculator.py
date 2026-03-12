import math

def calculate_relativity():
    print("--- Special Relativity Calculator ---")
    
    # Constants
    c = 2.999729456e8  # speed of light in m/s
    
    # Inputs
    try:
        m_input = input("Enter mass in kg (default 1): ")
        m = float(m_input) if m_input else 1.0
        
        v_input = input("Enter velocity as fraction of c (e.g. 0.5) or in m/s (default 0.47349e-8 * c): ")
        if not v_input:
             v = 0.47349e-8 * c
        elif float(v_input) < 1.0 and float(v_input) > -1.0: # Assume fraction of c if small
             v = float(v_input) * c
        else:
             v = float(v_input)
             
        if v >= c:
            print("Error: Velocity must be less than the speed of light.")
            return

    except ValueError:
        print("Invalid input. Using defaults.")
        m = 1.0
        v = 0.47349e-8 * c

    print(f"\nMass: {m} kg")
    print(f"Velocity: {v:.3e} m/s ({v/c:.10f} c)")

    # Step 1: Lorentz factor
    gamma = 1 / math.sqrt(1 - (v/c)**2)
    print(f"Lorentz factor (gamma): {gamma:.10f}")

    # Step 2: Relativistic momentum
    p = gamma * m * v

    # Step 3: Total energy
    E_total = math.sqrt((m * c**2)**2 + (p * c)**2)

    # Step 4: Kinetic energy
    E_kinetic = E_total - m * c**2

    # Step 5: Ratios
    ratio_total_to_rest = E_total / (m * c**2)
    ratio_kinetic_to_rest = E_kinetic / (m * c**2)

    # Output
    print(f"Total energy: {E_total:.3e} J")
    print(f"Kinetic energy: {E_kinetic:.3e} J")
    print(f"Total energy / rest energy: {ratio_total_to_rest:.10f}")
    print(f"Kinetic energy / rest energy: {ratio_kinetic_to_rest:.10f}")

if __name__ == "__main__":
    calculate_relativity()
