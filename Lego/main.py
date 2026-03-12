
"""
Lego Build Planner: Describe what you want to build in natural language, and get a step-by-step Lego build plan.
"""

def generate_lego_plan(prompt):
    # Placeholder for AI/LLM integration. Replace with OpenAI API or similar for real use.
    # For now, return a simple hardcoded plan for demonstration.
    if "car" in prompt.lower():
        return [
            "Step 1: Gather 4 wheels, 2 axles, 1 base plate, and bricks for the body.",
            "Step 2: Attach the axles and wheels to the base plate.",
            "Step 3: Build up the car body with bricks, leaving space for windows.",
            "Step 4: Add a steering wheel and seats.",
            "Step 5: Decorate with lights and details."
        ]
    elif "house" in prompt.lower():
        return [
            "Step 1: Gather base plate, bricks for walls, windows, and a door.",
            "Step 2: Build the walls on the base plate, leaving gaps for windows and door.",
            "Step 3: Insert windows and door into the gaps.",
            "Step 4: Add a roof using sloped bricks.",
            "Step 5: Decorate the house with flowers and details."
        ]
    else:
        return [
            "Step 1: Gather a variety of Lego bricks and plates.",
            "Step 2: Start with a sturdy base.",
            "Step 3: Build up the main shape as described.",
            "Step 4: Add details and decorations to match your idea.",
            "Step 5: Refine and adjust for stability."
        ]

def main():
    print("Welcome to the Lego Build Planner!")
    prompt = input("Describe what you want to build in Lego form: ")
    plan = generate_lego_plan(prompt)
    print("\nLego Build Plan:")
    for step in plan:
        print(step)

if __name__ == "__main__":
    main()
