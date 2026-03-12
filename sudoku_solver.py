import threading
import time
import tkinter as tk
from pynput.keyboard import Controller

keyboard = Controller()
pressing = False

def press_loop():
    global pressing
    while pressing:
        keyboard.press('m')
        keyboard.release('m')
        time.sleep(0.2)  # press interval

def start_pressing():
    global pressing
    if not pressing:
        pressing = True
        threading.Thread(target=press_loop, daemon=True).start()

def stop_pressing():
    global pressing
    pressing = False

# GUI
root = tk.Tk()
root.title("M Key Auto Presser")
root.geometry("300x150")

start_btn = tk.Button(root, text="Start Pressing M", font=("Arial", 12), command=start_pressing)
start_btn.pack(pady=10)

stop_btn = tk.Button(root, text="Stop", font=("Arial", 12), command=stop_pressing)
stop_btn.pack(pady=10)

root.mainloop()
