import time
import pyautogui

x_button_location = 220
y_button_location = 260


total_time = 24.0 * 60.0 * 60.0  # in seconds
cycle_rate = 60.0 * 60.0  # in seconds
open_time = 60.0  # in seconds
close_time = cycle_rate - open_time

start_time = time.time()


def elapsed_time():
    now = time.time()
    return now - start_time


while total_time > elapsed_time():
    pyautogui.click(x_button_location, y_button_location)
    time.sleep(close_time)
    pyautogui.click(x_button_location, y_button_location)
    time.sleep(open_time)




