"""Quick key presser - presses 1 2 3 4 5 a b m as fast as possible"""
import keyboard
import time

keys = ['1', '2', '3', '4', '5', 'a', 'b', 'm']

print(f"Pressing keys: {keys}")
print("Press Ctrl+C to stop, or wait 3 seconds...")

time.sleep(3)

for key in keys:
    keyboard.press(key)
    time.sleep(0.01)  # Minimal delay
    keyboard.release(key)

print("Done!")