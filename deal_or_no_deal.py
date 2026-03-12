import tkinter as tk
from tkinter import messagebox

# New ITV Deal or No Deal prize values
BLUE_VALUES = [0.01, 0.10, 0.50, 1, 5, 10, 50, 100, 250, 500, 750]
RED_VALUES  = [1000, 2000, 3000, 4000, 5000, 7500,
               10000, 25000, 50000, 75000, 100000]

BOX_VALUES = BLUE_VALUES + RED_VALUES

class DealNoDealApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deal or No Deal - Offer Checker")
        
        self.remaining = BOX_VALUES.copy()
        self.buttons = {}
        
        frame = tk.Frame(root)
        frame.pack(pady=10)

        # Left column (blue values)
        for i, value in enumerate(BLUE_VALUES):
            btn = tk.Button(frame, text=f"£{value:,}", width=10,
                            fg="blue",
                            command=lambda v=value: self.remove_box(v))
            btn.grid(row=i, column=0, padx=10, pady=2, sticky="w")
            self.buttons[value] = btn

        # Right column (red values)
        for i, value in enumerate(RED_VALUES):
            btn = tk.Button(frame, text=f"£{value:,}", width=10,
                            fg="red",
                            command=lambda v=value: self.remove_box(v))
            btn.grid(row=i, column=1, padx=10, pady=2, sticky="e")
            self.buttons[value] = btn
        
        # Banker offer entry
        self.offer_var = tk.DoubleVar()
        tk.Label(root, text="Banker's Offer (£):").pack()
        tk.Entry(root, textvariable=self.offer_var).pack()
        
        tk.Button(root, text="Check Offer", command=self.check_offer).pack(pady=10)

        # Live EV display
        self.ev_label = tk.Label(root, text="", font=("Arial", 12, "bold"))
        self.ev_label.pack(pady=5)

        self.update_ev()  # show initial EV
    
    def remove_box(self, value):
        if value in self.remaining:
            self.remaining.remove(value)
            self.buttons[value].config(state="disabled", relief="sunken")
            self.update_ev()
    
    def update_ev(self):
        if self.remaining:
            ev = sum(self.remaining) / len(self.remaining)
            self.ev_label.config(text=f"Expected Value (EV): £{ev:,.2f}")
        else:
            self.ev_label.config(text="No boxes left!")
    
    def check_offer(self):
        if not self.remaining:
            messagebox.showerror("Error", "No boxes left!")
            return
        
        ev = sum(self.remaining) / len(self.remaining)
        try:
            offer = self.offer_var.get()
        except:
            messagebox.showerror("Error", "Invalid offer amount")
            return
        
        # Calculate percentage difference
        percent_diff = ((offer - ev) / ev) * 100 if ev > 0 else 0
        
        if offer > ev:
            verdict = "Good deal (Above EV)"
        elif offer == ev:
            verdict = "Fair deal (Equal to EV)"
        else:
            verdict = "Undervalue (Below EV)"
        
        messagebox.showinfo("Result",
            f"Expected Value: £{ev:,.2f}\n"
            f"Banker's Offer: £{offer:,.2f}\n"
            f"Difference: {percent_diff:+.2f}%\n\n"
            f"Verdict: {verdict}"
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = DealNoDealApp(root)
    root.mainloop()
