import datetime
import time
import os
import tkinter as tk
from tkinter import ttk
import threading

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def calculate_due_date():
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

    return due_date

def get_current_progress():
    """Get current pregnancy progress based on current date"""
    # Milestone: On November 14, 2025, was 12 weeks and 3 days pregnant
    milestone_date = datetime.date(2025, 11, 14)
    weeks_at_milestone = 12
    days_at_milestone = 3

    # Convert milestone gestational age to total days
    days_at_milestone_total = (weeks_at_milestone * 7) + days_at_milestone

    # Get current date
    current_date = datetime.date.today()

    # Calculate days elapsed since milestone
    days_elapsed = (current_date - milestone_date).days

    # Current gestational age in days
    current_days_pregnant = days_at_milestone_total + days_elapsed

    # Convert to weeks
    current_weeks = current_days_pregnant / 7
    total_weeks = 40

    # Calculate percentage
    percentage = min((current_weeks / total_weeks) * 100, 100)  # Cap at 100%

    return current_weeks, total_weeks, percentage

def format_time_remaining(time_delta):
    """Format timedelta into weeks, days, hours, minutes, seconds"""
    total_seconds = int(time_delta.total_seconds())

    weeks = total_seconds // (7 * 24 * 3600)
    remaining_seconds = total_seconds % (7 * 24 * 3600)

    days = remaining_seconds // (24 * 3600)
    remaining_seconds %= (24 * 3600)

    hours = remaining_seconds // 3600
    remaining_seconds %= 3600

    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    return weeks, days, hours, minutes, seconds

class PregnancyTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Baby Girl Pregnancy Tracker")
        self.root.geometry("500x400")
        self.root.configure(bg='#FFE6F7')  # Light pink background

        # Initialize data
        self.due_date = calculate_due_date()
        self.update_progress()

        # Create GUI elements
        self.create_widgets()

        # Start the timer update thread
        self.running = True
        self.timer_thread = threading.Thread(target=self.update_timer, daemon=True)
        self.timer_thread.start()

    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="👶 Baby Girl Pregnancy Tracker 👶",
                              font=('Arial', 18, 'bold'), bg='#FFE6F7', fg='#8B008B')
        title_label.pack(pady=20)

        # Progress frame
        progress_frame = tk.Frame(self.root, bg='#FFE6F7')
        progress_frame.pack(pady=10)

        # Current progress label
        self.progress_label = tk.Label(progress_frame,
                                      text=f"Current Progress: {self.weeks_whole} weeks and {self.days_extra} days",
                                      font=('Arial', 12), bg='#FFE6F7')
        self.progress_label.pack()

        # Percentage label
        self.percentage_label = tk.Label(progress_frame,
                                        text=f"Pregnancy Completion: {self.percentage:.6f}%",
                                        font=('Arial', 12, 'bold'), bg='#FFE6F7', fg='#FF1493')
        self.percentage_label.pack()

        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal",
                                           length=300, mode="determinate",
                                           maximum=100, value=self.percentage)
        self.progress_bar.pack(pady=10)

        # Due date frame
        date_frame = tk.Frame(self.root, bg='#FFE6F7')
        date_frame.pack(pady=10)

        # Due date label
        self.due_date_label = tk.Label(date_frame,
                                      text=f"Due Date: {self.due_date.strftime('%B %d, %Y')}",
                                      font=('Arial', 12), bg='#FFE6F7')
        self.due_date_label.pack()

        # Today's date label
        self.today_label = tk.Label(date_frame,
                                   text=f"Today's Date: {datetime.date.today().strftime('%B %d, %Y')}",
                                   font=('Arial', 10), bg='#FFE6F7', fg='#666666')
        self.today_label.pack()

        # Timer frame
        timer_frame = tk.Frame(self.root, bg='#FFE6F7')
        timer_frame.pack(pady=20)

        # Timer title
        timer_title = tk.Label(timer_frame, text="Time Remaining Until Due Date:",
                              font=('Arial', 14, 'bold'), bg='#FFE6F7')
        timer_title.pack()

        # Live countdown timer
        self.timer_label = tk.Label(timer_frame, text="",
                                   font=('Arial', 16, 'bold'), fg='#FF4500', bg='#FFE6F7')
        self.timer_label.pack(pady=10)

        # Update button
        update_button = tk.Button(self.root, text="Refresh", command=self.refresh_data,
                                 bg='#FFB6C1', font=('Arial', 10))
        update_button.pack(pady=10)

    def update_progress(self):
        """Update pregnancy progress data"""
        current_weeks, total_weeks, percentage = get_current_progress()
        self.weeks_whole = int(current_weeks)
        self.days_extra = int((current_weeks - self.weeks_whole) * 7)
        self.percentage = percentage

    def update_timer(self):
        """Update the countdown timer in a separate thread"""
        while self.running:
            try:
                now = datetime.datetime.now()
                due_datetime = datetime.datetime.combine(self.due_date, datetime.time(0, 0, 0))
                time_remaining = due_datetime - now

                if time_remaining.total_seconds() > 0:
                    weeks, days, hours, minutes, seconds = format_time_remaining(time_remaining)
                    timer_text = f"{weeks} weeks, {days} days\n{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    timer_text = "BABY GIRL IS DUE!\n🎉 CONGRATULATIONS! 🎉"

                # Update timer label on main thread
                self.root.after(0, lambda: self.timer_label.config(text=timer_text))
                time.sleep(1)
            except Exception as e:
                break

    def refresh_data(self):
        """Refresh all data and update display"""
        self.update_progress()

        # Update labels
        self.progress_label.config(text=f"Current Progress: {self.weeks_whole} weeks and {self.days_extra} days")
        self.percentage_label.config(text=f"Pregnancy Completion: {self.percentage:.6f}%")
        self.progress_bar.config(value=self.percentage)
        self.today_label.config(text=f"Today's Date: {datetime.date.today().strftime('%B %d, %Y')}")

    def stop(self):
        """Stop the timer thread"""
        self.running = False

def main_console():
    """Console version of the pregnancy tracker"""
    due_date = calculate_due_date()
    current_weeks, total_weeks, percentage = get_current_progress()

    print("*** Baby Girl Pregnancy Tracker ***")
    print("=" * 50)

    # Show static information first
    weeks_whole = int(current_weeks)
    days_extra = int((current_weeks - weeks_whole) * 7)
    print(f"Current Progress: {weeks_whole} weeks and {days_extra} days out of {total_weeks} weeks")
    print(f"Pregnancy Completion: {percentage:.6f}%")
    print(f"Due Date: {due_date.strftime('%B %d, %Y')}")
    print(f"Today's Date: {datetime.date.today().strftime('%B %d, %Y')}")
    print()

    # Then start the live timer
    try:
        while True:
            now = datetime.datetime.now()
            due_datetime = datetime.datetime.combine(due_date, datetime.time(0, 0, 0))
            time_remaining = due_datetime - now

            weeks, days, hours, minutes, seconds = format_time_remaining(time_remaining)

            # Move cursor up to overwrite previous timer
            print(f"\rTime Remaining: {weeks} weeks, {days} days, {hours:02d}:{minutes:02d}:{seconds:02d}", end="", flush=True)

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nTimer stopped.")

def main_gui():
    """GUI version of the pregnancy tracker"""
    root = tk.Tk()
    app = PregnancyTrackerGUI(root)

    def on_closing():
        app.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "console":
        main_console()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Simple test output
        due_date = calculate_due_date()
        current_weeks, total_weeks, percentage = get_current_progress()
        weeks_whole = int(current_weeks)
        days_extra = int((current_weeks - weeks_whole) * 7)

        print("*** Baby Girl Pregnancy Tracker ***")
        print("=" * 50)
        print(f"Current Progress: {weeks_whole} weeks and {days_extra} days out of {total_weeks} weeks")
        print(f"Pregnancy Completion: {percentage:.6f}%")
        print(f"Due Date: {due_date.strftime('%B %d, %Y')}")
        print(f"Today's Date: {datetime.date.today().strftime('%B %d, %Y')}")
    else:
        main_gui()
