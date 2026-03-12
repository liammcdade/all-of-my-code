# Script to fix the due date in baby.py
with open('APPS/baby.py', 'r') as f:
    content = f.read()

# Replace the function
old_function = '''def calculate_due_date():
    """Calculate due date based on pregnancy milestone"""
    # On November 14, 2025, was 12 weeks and 3 days pregnant
    milestone_date = datetime.date(2025, 11, 14)
    weeks_at_milestone = 12
    days_at_milestone = 3

    # Convert to total days pregnant at milestone
    days_pregnant_at_milestone = (weeks_at_milestone * 7) + days_at_milestone

    # Full term is 40 weeks = 280 days
    total_pregnancy_days = 40 * 7  # 280 days

    # Days remaining at milestone
    days_remaining_at_milestone = total_pregnancy_days - days_pregnant_at_milestone

    # Due date = milestone date + remaining days
    due_date = milestone_date + datetime.timedelta(days=days_remaining_at_milestone)

    return due_date'''

new_function = '''def calculate_due_date():
    """Calculate due date based on pregnancy milestone"""
    # User corrected: due date is May 24, 2026
    return datetime.date(2026, 5, 24)'''

if old_function in content:
    new_content = content.replace(old_function, new_function)
    with open('APPS/baby.py', 'w') as f:
        f.write(new_content)
    print("Due date function successfully updated to May 24, 2026!")
else:
    print("Old function not found in file")
    # Try partial replacement
    partial_old = "# On November 14, 2025, was 12 weeks and 3 days pregnant"
    partial_new = "# User corrected: due date is May 24, 2026\n    return datetime.date(2026, 5, 24)"
    if partial_old in content:
        new_content = content.replace(partial_old, partial_new)
        with open('APPS/baby.py', 'w') as f:
            f.write(new_content)
        print("Partial replacement done")
    else:
        print("Partial text not found either")



