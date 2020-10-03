import time
import datetime
import pyautogui
from waferscreen.inst_control.labjack import U3

x_button_location = 220
y_button_location = 260


total_time = 24.0 * 60.0 * 60.0  # in seconds
cycle_rate = 60.0 * 60.0  # in seconds
open_time = 60.0  # in seconds
close_time = cycle_rate - (3.0 * open_time)

start_time = time.time()


def elapsed_time():
    now = time.time()
    return now - start_time

labjack = U3(auto_init=True, verbose=True)

print("Starting heat switch clicker in 10 seconds")
time.sleep(10)
while total_time > elapsed_time():
    print("Heat Switch Closed Command", datetime.datetime.now())
    pyautogui.click(x_button_location, y_button_location)
    time.sleep(open_time)
    labjack.alive_test(voltage=3.0, zero_after=True)
    time.sleep(close_time)

    print("Heat Switch Open Command", datetime.datetime.now())
    pyautogui.click(x_button_location, y_button_location)
    time.sleep(open_time)
    labjack.alive_test(voltage=3.0, zero_after=True)
print("Heat Switch Closed Command", datetime.datetime.now())
pyautogui.click(x_button_location, y_button_location)
time.sleep(open_time)
labjack.alive_test(voltage=3.0, zero_after=True)



