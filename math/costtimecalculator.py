import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading

class VPCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VP Time Calculator")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        # Variables
        self.vp_per_second = tk.DoubleVar(value=1.0)
        self.game_speed = tk.DoubleVar(value=1.0)
        self.current_vp = tk.DoubleVar(value=0.0)
        self.target_vp = tk.DoubleVar(value=100.0)
        self.time_remaining = tk.DoubleVar(value=0.0)
        self.is_counting = False
        self.countdown_thread = None
        
        self.create_widgets()
        self.calculate_time()
        
    def create_widgets(self):
        # Style
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10))
        style.configure("TEntry", font=("Arial", 10))
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # VP per Second
        ttk.Label(main_frame, text="VP per Second:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.vp_per_second, width=15).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        self.vp_per_second.trace("w", lambda *args: self.calculate_time())
        
        # Game Speed
        ttk.Label(main_frame, text="Game Speed:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.game_speed, width=15).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        self.game_speed.trace("w", lambda *args: self.calculate_time())
        
        # Current VP
        ttk.Label(main_frame, text="Current VP:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.current_vp, width=15).grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        self.current_vp.trace("w", lambda *args: self.calculate_time())
        
        # Target VP
        ttk.Label(main_frame, text="Target VP:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.target_vp, width=15).grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        self.target_vp.trace("w", lambda *args: self.calculate_time())
        
        # Time Remaining
        ttk.Label(main_frame, text="Time Remaining:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.time_label = ttk.Label(main_frame, text="00:00:00", font=("Arial", 14, "bold"))
        self.time_label.grid(row=4, column=1, sticky=tk.W, pady=(10, 5))
        
        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=2, pady=(10, 15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
        self.start_btn = ttk.Button(button_frame, text="Start Countdown", command=self.toggle_countdown)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Reset", command=self.reset_countdown).pack(side=tk.LEFT, padx=5)
        
        # Current VP Display
        ttk.Label(main_frame, text="Current Progress:").grid(row=7, column=0, sticky=tk.W, pady=(15, 0))
        self.current_vp_label = ttk.Label(main_frame, text="0 VP (0.0%)", font=("Arial", 12))
        self.current_vp_label.grid(row=7, column=1, sticky=tk.W, pady=(15, 0))
        
    def calculate_time(self):
        try:
            # Calculate time to reach target
            required_vp = self.target_vp.get() - self.current_vp.get()
            effective_rate = self.vp_per_second.get() * self.game_speed.get()
            
            if required_vp <= 0 or effective_rate <= 0:
                self.time_remaining.set(0)
                self.time_label.config(text="00:00:00")
                self.progress['value'] = 100
                return
                
            time_needed = required_vp / effective_rate
            self.time_remaining.set(time_needed)
            
            # Update display
            self.time_label.config(text=self.format_time(time_needed))
            
            # Calculate progress
            total_vp = self.target_vp.get()
            current_progress = (self.current_vp.get() / total_vp) * 100
            self.progress['value'] = current_progress
            
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        
    def toggle_countdown(self):
        if not self.is_counting:
            self.start_countdown()
        else:
            self.stop_countdown()
            
    def start_countdown(self):
        # Check if we've already reached target
        if self.current_vp.get() >= self.target_vp.get():
            messagebox.showinfo("Info", "Already reached target VP!")
            return
            
        self.is_counting = True
        self.start_btn.config(text="Stop Countdown")
        self.countdown_thread = threading.Thread(target=self.countdown_loop, daemon=True)
        self.countdown_thread.start()
        
    def countdown_loop(self):
        while self.is_counting and self.current_vp.get() < self.target_vp.get():
            time.sleep(1.0 / self.game_speed.get())
            
            # Calculate new current VP
            new_vp = self.current_vp.get() + self.vp_per_second.get() * (1.0 / self.game_speed.get())
            self.current_vp.set(min(new_vp, self.target_vp.get()))
            
            # Update UI
            self.root.after(0, self.update_display)
            
        # Check if we reached target
        if self.current_vp.get() >= self.target_vp.get():
            self.root.after(0, lambda: messagebox.showinfo("Complete", "Target VP reached!"))
            self.root.after(0, self.stop_countdown)
            
    def stop_countdown(self):
        self.is_counting = False
        self.start_btn.config(text="Start Countdown")
        
    def reset_countdown(self):
        self.stop_countdown()
        self.current_vp.set(0.0)
        self.calculate_time()
        self.current_vp_label.config(text="0 VP (0.0%)")
        
    def update_display(self):
        percentage = (self.current_vp.get() / self.target_vp.get()) * 100
        self.current_vp_label.config(text=f"{self.current_vp.get():.1f} VP ({percentage:.1f}%)")
        self.calculate_time()
        
def main():
    root = tk.Tk()
    app = VPCalculatorApp(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()
