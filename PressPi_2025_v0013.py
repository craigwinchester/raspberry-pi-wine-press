#!/usr/bin/env python3
# -----------------LoFi Wines---Wine Press 2020-------------#
# -----------------Version 0.0.03--------------4/29/2020----#
# -----------------Craig Winchester-------------------------#
# 0.0.04 --- Added Clock-----------------------------------#
# 0.0.07 --- Warnings . door/valve--------------------------#
#        --- removed individual program threads
#        --- only numbers allowed in setToBar
#        --- turned spinTolocation into threads
# 0.0.08 --- pressProgram now has exception() =
#        --- Emergency button now stops pressProgram
# 0.0.10 --- New Pressure Transducer / Arduino
####### 2025 UPDATES-------------------------------------
# 0005 - Added Program Editor.
# 0010 - getCurrentBar re-write.
# 0011 - getCurrent bar now a global variable with a thread running in background. pressure_updater
# 0012 - more edits to getCurrentBar. Also new Arduino sketch for this.
# 0013 - changed gauge to a digital readout. Easier readblity. seems faster.


import ctypes
import tkinter as tk
from tkinter import simpledialog, messagebox
import RPi.GPIO as GPIO
import time
from datetime import datetime
import board
import busio
import tk_tools
import threading
import tkinter.scrolledtext as ScrolledText
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import json

ser=serial.Serial("/dev/ttyUSB0", 9600)
ser.baudrate=9600

GPIO.setmode(GPIO.BCM)

pinList = [17, 27, 22, 23, 24, 25, 16, 26]

pressurePinList = [16, 26]
vacuumPinList = [23, 24, 25]

pressure_data = 0.0

count = 0
spinning_flag = 0  # 0 = false, 1 = true
pressure_flag = 0  # inflate=1 deflate=2 nothing=0
program_flag = 0
emerg_flag = 0

topTime = 5  # --- timing variables to set location. adjust as needed
drainTime = 1
bottomTime = 10
fullDeflate = 0.6 #set to 0.001 when ready! 0.6 is good for testing

# Define the correct file path
FILE_PATH = "/home/pi/Documents/WinePress2020/programs.json"

GPIO.setup(pinList, GPIO.OUT, initial=GPIO.HIGH)

# Global programs list
programs = []

# Debugging function to verify button press execution
def debug_button_press(button_name):
    print(f"Button '{button_name}' was clicked.")

# Debugging function to track program start
def debug_program_start(program_name):
    print(f"Starting pressProgram for: {program_name}")


# ------------------------------------BUTTON SETUP----------
# --This is our position sensor on the press---------------

def button_callback(channel):
    global count
    count = count + 1
    printBox("Rotation counter:", count)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(21, GPIO.FALLING, callback=button_callback, bouncetime=500)


# ----------------------------get Current Bar-----
def getCurrentBar():
        try:
            currentBar = ser.readline().strip().decode('utf-8').strip()
            return float(currentBar)  # Ensure data is returned as a float
        except (ValueError, AttributeError):
            print(f"Invalid data received: {currentBar}")
            return 0.0  # Return a default value for stability

# Background thread to refresh pressure data
def pressure_updater():
    global pressure_data
    while True:
        pressure_data = getCurrentBar()
        now = datetime.now()
        #printBox("PSI: ", pressure_data)
        time.sleep(0.25)  # 250ms refresh rate

# --------------------------Update Gauge--------------------
def update_gauge():
    bar_gauge.config(text=f"{pressure_data} BAR")
    bar_gauge.after(50, update_gauge)

# ------------------MyTime----------------------------------
def myTime():
    string = time.strftime('%H:%M:%S %p')
    lbl.config(text=string)
    lbl.after(1000, myTime)


# ----------------Time convert-----------------------
def convertTime(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


# ------------------------print to console box---------------
def printBox(*args):
    argCount = len(args)
    for elem in args:
        text_box.insert(tk.END, str(elem) + " ")
    text_box.insert(tk.INSERT, "\n")
    text_box.see(tk.END)


# --------------------------------------------------------------------
# -----------------CLASS----------pressure----------------------------
class Pressure:
    def __init__(self, bar, startTime):
        self.bar = bar
        self.startTime = startTime

    def inflateToBar(self):
        global elapsedTime, emerg_flag, pressure_flag
        while pressure_data < self.bar and emerg_flag == 0:  # turn on pressure
            GPIO.output(pressurePinList, GPIO.LOW)
            pressure_flag = 1
            if pressure_data is None:
                print("Failed to read current pressure. RETRYING...")
                continue
            printBox("Inflating: ", pressure_data)
            time.sleep(1)
        else:  # turn off pressure
            GPIO.output(pressurePinList, GPIO.HIGH)
            pressure_flag = 0
            elapsedTime = time.time() - self.startTime
            return elapsedTime

    def deflateToBar(self):
        global emerg_flag, pressure_flag
        while pressure_data > self.bar and emerg_flag == 0:
            GPIO.output(vacuumPinList, GPIO.LOW)
            pressure_flag = 2
            if pressure_data is None:
                print("Failed to read current pressure. RETRYING...")
                continue
            printBox("Deflating:", pressure_data)
            time.sleep(1)
        else:  # turn off vacuum
            GPIO.output(vacuumPinList, GPIO.HIGH)
            pressure_flag = 0

    def deflate():
        # GPIO 23 = Pin16 = Turn on Vacuum pump
        # GPIO 24 & 25 = Pin18 & 22 = OPEN DEFLATE Solenoids 24volt ---
        # GPIO 16 & 26 = Pin36 & 37 = CLOSE INFLATE Solenoids 24volt ---
        global spinning_flag, pressure_flag, program_flag
        if spinning_flag == 0 and pressure_flag != 1 and program_flag == 0:  # check that vacuum pump is not on. Check that motor is not rotating.
            if GPIO.input(24) == True and GPIO.input(25) == True and GPIO.input(23) == True:
                Button_vacuum.configure(bg="red")
                printBox("Vacumm On")
                text_box.see(tk.END)
                pressure_flag = 2
                GPIO.output(pressurePinList, GPIO.HIGH)
                GPIO.output(vacuumPinList, GPIO.LOW)
            else:
                pressure_flag = 0
                Button_vacuum.configure(bg="light slate gray")
                printBox("Vacumm Off")
                GPIO.output(vacuumPinList, GPIO.HIGH)
        else:
            printBox("error-----Cant decompress while spinning or changing pressure\n")

    def inflate():
        # GPIO 24 & 25 = Pin18 & 22 = OPEN DEFLATE Solenoids 24volt ---
        # GPIO 16 & 26 = Pin36 & 37 = CLOSE INFLATE Solenoids 24volt ---
        global spinning_flag, pressure_flag, program_flag
        if spinning_flag == 0 and pressure_flag != 2 and program_flag == 0:
            if GPIO.input(16) == True and GPIO.input(26) == True:
                pressure_flag = 1
                Button_pressure.configure(bg="red")
                printBox("Pressure On")
                GPIO.output(pressurePinList, GPIO.LOW)
                GPIO.output(vacuumPinList, GPIO.HIGH)
            else:
                pressure_flag = 0
                Button_pressure.configure(bg="light slate gray")
                printBox("Pressure Off")
                GPIO.output(pressurePinList, GPIO.HIGH)
        else:
            printBox("error-----cant inflate while spinning or changing pressure\n")


# ----------------------------------------------------------------------------------
# ----------------------CLASS-----pressProgram--------------------------------------
class pressProgram(threading.Thread):
    def __init__(self, name, program):
        threading.Thread.__init__(self)
        self.name = name
        self.program = program
        debug_program_start(name)

    def run(self):
        global program_flag, emerg_flag, spinning_flag
        if program_flag == 0 and spinning_flag == 0 and pressure_flag == 0:
            printBox(f"Running program: {self.name}")
            program_flag = 1
            #---turn buttons red
            if threading.currentThread().getName() == "White":
                Button_programOne.configure(bg="red")
            if threading.currentThread().getName() == "Red":
                Button_programTwo.configure(bg="red")
            if threading.currentThread().getName() == "Custom":
                Button_programThree.configure(bg="red")
            starting_time = time.time()
            printBox("RunProgram - " + threading.currentThread().getName())
            tk.messagebox.showwarning(title = "!", message = "Door Closed?")
            tk.messagebox.showwarning(title = "!", message = "Valve Closed?")
            print("Program started successfully")
            try:
                while True:
                    # ------------------------------------------SPIN TO DRAIN POS.
                    printBox("Spinning to Drain Position")
                    breakupRotations(1)
                    time.sleep(2)  # brief pause
                    # ------------------------------------------------RUN PROGRAM-- start looping...
                    for i in range(len(self.program)):
                        printBox("-----Stage:", self.program[i]["stage"])
                        for j in range(self.program[i]["cycles"]):
                            printBox("-----Cycle:", j + 1)
                           # --------------------------------------------------INITIAL INFLATE.
                           #----assumes bag was fully deflated to start with
                            printBox("Initial Inflate to Bar:", self.program[i]["maxPressure"])
                            Pressure(self.program[i]["maxPressure"], time.time()).inflateToBar()
                            printBox("Time to inflate:", elapsedTime)
                            time.sleep(1)  # brief pause
                            # --------------------------------------------------START TIMER
                            pTime = self.program[i]["pressureTime"]
                            printBox("Hold Pressure between:", self.program[i]["resetPressure"], " - ",
                                     self.program[i]["maxPressure"])
                            printBox("For", self.program[i]["pressureTime"], "seconds")
                            t_end = time.time() + pTime
                            while time.time() < t_end:
                                time.sleep(1)
                                pTime = pTime - 1
                                if pressure_data < self.program[i]["resetPressure"]:
                                    printBox("-----REPRESSURIZING-----")
                                    startTime = time.time()
                                    Pressure((self.program[i]["maxPressure"]), startTime).inflateToBar()
                                    t_end = t_end + elapsedTime
                                else:
                                    printBox("pressure holding - ", pTime)
                            else:
                                printBox("Time Elaspsed")
                                time.sleep(1)  # brief pause
                            # --------------------------------------------------DEFLATE
                            printBox("-----DEFLATE")
                            Pressure(fullDeflate, time.time()).deflateToBar()
                            time.sleep(1)  # brief pause
                            # --------------------------------------------------ROTATE
                            printBox("Break up rotations: ", self.program[i]["breakUpRotations"])
                            breakupRotations(self.program[i]["breakUpRotations"])
                            time.sleep(1)  # brief pause
                            printBox("---Cycle Finished---")
                        printBox("---Stage Finished---")
                    printBox("---Program Finished---")
                    totalTime = time.time() - starting_time
                    printBox("Total Time: ", convertTime(totalTime))
                    program_flag = 0
                    Button_programThree.configure(bg="light slate gray")
                    Button_programTwo.configure(bg="light slate gray")
                    Button_programOne.configure(bg="light slate gray")
                    #timestamp = datetime.datetime.now().isoformat()
                    #filename = str(self.name) + "_" + str(timestamp) + ".png"
                    #plt.savefig(filename)
                else:
                    printBox("program already running")
            finally:
                print('ended')

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


# ------------------------------BREAKUP ROTATIONS FUNCTION----
def breakupRotations(n):
    global count
    count = 0
    GPIO.output(27, GPIO.LOW)
    while True:
        if count >= n:
            timer = threading.Timer(1, stopRotation)
            timer.start()
            break


# -----------------------------STOP ROTATION FUNCTION---------
def stopRotation():
    global count, spinning_flag
    count = 0
    spinning_flag = 0
    GPIO.output(27, GPIO.HIGH)
    Button_top.configure(bg="light slate gray")
    Button_drain.configure(bg="light slate gray")
    Button_bottom.configure(bg="light slate gray")

#---------------------------------------------------------------------------------#
#-------------------Spin Class----------------------------------------------------#
class Spin:
    def __init__(self, loc):
        self.loc = loc

    def left():
        global spinning_flag, pressure_flag, program_flag
        # am i inflating or deflating now?
        if pressure_flag == 0 and program_flag == 0:
            # am i turning to the right currently?
            if GPIO.input(27) == True:
                if GPIO.input(17) == True:
                    printBox("Turning Left")
                    Button_left.configure(bg="red")
                    GPIO.output(17, GPIO.LOW)  # turn left
                    spinning_flag = 1
                else:
                    printBox("Stop Turning Left")
                    Button_left.configure(bg="light slate gray")
                    GPIO.output(17, GPIO.HIGH)  # stop turning left
                    spinning_flag = 0
        else:
            printBox("error-----Cant spin while adjusting pressure!")

    def right():
        global spinning_flag, pressure_flag, program_flag
        # am i inflating or deflating now?
        if pressure_flag == 0 and program_flag == 0:
            # am i turning to the left currently?
            if GPIO.input(17) == True:
                if GPIO.input(27) == True:
                    printBox("Turning Right")
                    Button_right.configure(bg="red")
                    GPIO.output(27, GPIO.LOW)  # turn right
                    spinning_flag = 1
                else:
                    printBox("Stop Turning Right")
                    Button_right.configure(bg="light slate gray")
                    GPIO.output(27, GPIO.HIGH)  # stop turning right
                    spinning_flag = 0
        else:
            printBox("error-----Cant spin while adjusting pressure!\n")

#--------------------------SpinToLocation---------------------
def spinToLocation(loc):
    global count, spinning_flag, pressure_flag, program_flag
    count = 0
    location = int(loc)

    if pressure_flag == 0 and program_flag == 0 and spinning_flag == 0:
        if threading.currentThread().getName() == "topSpin":
            Button_top.configure(bg="red")
            printBox("Rotating to fill position")
        if threading.currentThread().getName() == "drainSpin":
            Button_drain.configure(bg="red")
            printBox("Rotating to drain position")
        if threading.currentThread().getName() == "bottomSpin":
            Button_bottom.configure(bg="red")
            printBox("Rotating door to bottom position")
        GPIO.output(27, GPIO.LOW)
        spinning_flag = 1
        while count < 1:
            time.sleep(1)
        else:
            timer = threading.Timer(location, stopRotation)
            timer.start()
    else:
        printBox("Nope... I'm busy!")



#------------------Threads---------------------------
def setToBar_thread():
    global pressure_flag, spinning_flag, program_flag
    if pressure_flag == 0 and spinning_flag == 0 and program_flag == 0:
        if len(Entry_bar.get()) == 0 or str(Entry_bar.get()).isalpha() == True :
            printBox("null")
        else:
            p = float(Entry_bar.get())
            if p >= 0 and p < 1.80:
                if pressure_data < p:
                    printBox("Inflating to: ", str(p), " BAR")
                    Pressure(p, time.time()).inflateToBar()
                    time.sleep(1)  # adjust as needed
                if pressure_data > p:
                    printBox("Deflating to: ", str(p), " BAR")
                    Pressure(p, time.time()).deflateToBar()
                    time.sleep(1)
            else:
                printBox("must be between 0 and 1.8")
    else:
        printBox("nope...")

#------------------------------------------------------
# # Load programs from JSON file
def load_programs():
    global programs
    print(f"Attempting to open: {FILE_PATH}")  # Debugging print

    try:
        with open(FILE_PATH, "r") as f:
            loaded_programs = json.load(f)
            #print("Successfully loaded programs.json:", loaded_programs)

            if isinstance(loaded_programs, list):
                programs.clear()
                programs.extend(loaded_programs)  # Update global list
            else:
                print("Error: Expected list format but found:", type(loaded_programs))
                messagebox.showerror("File Error", "Invalid JSON format: Expected a list but found a dictionary.")
                return  # Prevent using an invalid structure

    except FileNotFoundError:
        print("Error: programs.json not found at", FILE_PATH)
        messagebox.showerror("File Error", f"programs.json not found at {FILE_PATH}. Creating a default configuration.")
        programs.append([
            {"stage": 1, "cycles": 3, "maxPressure": 0.2, "resetPressure": 0.16, "pressureTime": 180, "breakUpRotations": 3}
        ])
    except json.JSONDecodeError as e:
        print(f"Error: programs.json is corrupted or improperly formatted: {e}")
        messagebox.showerror("File Error", f"programs.json is corrupted or improperly formatted: {e}")
    except Exception as e:
        print(f"Unexpected error loading programs.json: {e}")
        messagebox.showerror("File Error", f"Unexpected error loading programs.json: {e}")

    #print("Final programs list after loading:", programs)  # Debugging print

# Save programs to JSON file
def save_programs():
    try:
        with open(FILE_PATH, "w") as f:
            json.dump(programs, f, indent=4)
            print("Successfully saved programs.json")
    except Exception as e:
        print(f"Error saving programs.json: {e}")
        messagebox.showerror("File Error", f"Error saving programs.json: {e}")

# Load programs initially
load_programs()

# Function to open editor dialog
def open_editor():
    global cycles_entries, maxPressure_entries, resetPressure_entries, pressureTime_entries, breakUpRotations_entries

    print("Opening editor. Current programs list:", programs)  # Debugging print

    # Mapping indices to program names
    program_names = {0: "White", 1: "Red", 2: "Custom"}

    def get_selected_program_index():
        return list(program_names.keys())[list(program_names.values()).index(program_var.get())]

    def load_program():
        selected_program = get_selected_program_index()
        print(f"Loading program {selected_program} ({program_names.get(selected_program, 'Unknown')}):", programs[selected_program])  # Debugging print

        # Clear previous entries
        for widget in editor.winfo_children():
            if isinstance(widget, tk.Entry) or isinstance(widget, tk.Label):
                widget.destroy()

        # Add column titles
        column_titles = ["Stage", "Cycles", "Max Pressure", "Reset Pressure", "Pressure Time", "Break Up Rotations"]
        for col, title in enumerate(column_titles):
            tk.Label(editor, text=title, font=("Arial", 10, "bold")).grid(row=1, column=col)

        cycles_entries.clear()
        maxPressure_entries.clear()
        resetPressure_entries.clear()
        pressureTime_entries.clear()
        breakUpRotations_entries.clear()

        for i, stage in enumerate(programs[selected_program]):
            tk.Label(editor, text=f"Stage {i+1}").grid(row=i+2, column=0)

            cycles_entry = tk.Entry(editor)
            cycles_entry.insert(0, stage.get("cycles", ""))
            cycles_entry.grid(row=i+2, column=1)
            cycles_entries.append(cycles_entry)

            maxPressure_entry = tk.Entry(editor)
            maxPressure_entry.insert(0, stage.get("maxPressure", ""))
            maxPressure_entry.grid(row=i+2, column=2)
            maxPressure_entries.append(maxPressure_entry)

            resetPressure_entry = tk.Entry(editor)
            resetPressure_entry.insert(0, stage.get("resetPressure", ""))
            resetPressure_entry.grid(row=i+2, column=3)
            resetPressure_entries.append(resetPressure_entry)

            pressureTime_entry = tk.Entry(editor)
            pressureTime_entry.insert(0, stage.get("pressureTime", ""))
            pressureTime_entry.grid(row=i+2, column=4)
            pressureTime_entries.append(pressureTime_entry)

            breakUpRotations_entry = tk.Entry(editor)
            breakUpRotations_entry.insert(0, stage.get("breakUpRotations", ""))
            breakUpRotations_entry.grid(row=i+2, column=5)
            breakUpRotations_entries.append(breakUpRotations_entry)

    def add_stage():
        selected_program = get_selected_program_index()
        programs[selected_program].append({"stage": len(programs[selected_program]) + 1, "cycles": 0, "maxPressure": 0.0, "resetPressure": 0.0, "pressureTime": 0, "breakUpRotations": 0})
        load_program()

    def remove_stage():
        selected_program = get_selected_program_index()
        if programs[selected_program]:
            programs[selected_program].pop()
        load_program()

    def save_changes():
        try:
            selected_program = get_selected_program_index()
            programs[selected_program] = []
            for i in range(len(cycles_entries)):
                new_stage = {
                    "stage": i + 1,
                    "cycles": int(cycles_entries[i].get()),
                    "maxPressure": float(maxPressure_entries[i].get()),
                    "resetPressure": float(resetPressure_entries[i].get()),
                    "pressureTime": int(pressureTime_entries[i].get()),
                    "breakUpRotations": int(breakUpRotations_entries[i].get())
                }
                programs[selected_program].append(new_stage)

            save_programs()
            root.attributes("-topmost", True)
            messagebox.showinfo("Success", "Program updated successfully!")
            editor.destroy()
            root.attributes("-topmost", False)
        except ValueError:
            root.attributes("-topmost", True)
            messagebox.showerror("Error", "Please enter valid numbers.")
            root.attributes("-topmost", False)


    editor = tk.Toplevel(root)

    screen_width = editor.winfo_screenwidth()
    screen_height = editor.winfo_screenheight()
    x = (screen_width // 2) - (950 // 2)
    y = (screen_height // 2) - (300 // 2)
    editor.title("Program Editor")
    editor.geometry(f"950x300+{x}+{y}")

    tk.Label(editor, text="Select Program: ").grid(row=0, column=0)
    program_var = tk.StringVar(editor)
    program_var.set("White")  # Default selection

    program_dropdown = tk.OptionMenu(editor, program_var, *program_names.values(), command=lambda _: load_program())
    program_dropdown.grid(row=0, column=3)

    tk.Button(editor, text="Add Stage", command=add_stage).grid(row=12, column=1)
    tk.Button(editor, text="Remove Stage", command=remove_stage).grid(row=12, column=2)
    tk.Button(editor, text="Save", command=save_changes).grid(row=12, column=4)

    cycles_entries = []
    maxPressure_entries = []
    resetPressure_entries = []
    pressureTime_entries = []
    breakUpRotations_entries = []

    load_program()  # Load first program immediately

# -------------------------TKINTER-------------------
root = tk.Tk()
root.title("Wine Press 2020")
root.geometry("1280x720")
root.configure(bg="SteelBlue3")

Button_left = tk.Button()
Button_left.grid(row=1, column=0, padx=(25,25), pady=(10,10))
Button_left.configure(bg="light slate gray")
Button_left.configure(text='''<-Left''', height="2", width="16",
                      command=lambda: Spin.left())

Button_right = tk.Button()
Button_right.grid(row=2, column=0, padx=(25,25), pady=(10,10))
Button_right.configure(bg="light slate gray")
Button_right.configure(text='''Right->''', height="2", width="16",
                       command=lambda: Spin.right())

Button_top = tk.Button()
Button_top.grid(row=0, column=1, padx=(25,25), pady=(10,10))
Button_top.configure(bg="light slate gray")
Button_top.configure(text='''Top''', height="2", width="16",
                     command=lambda: threading.Thread(name = "topSpin",
                                                      target = spinToLocation,
                                                      args = [topTime]).start())

Button_drain = tk.Button()
Button_drain.grid(row=1, column=1, padx=(25,25), pady=(10,10))
Button_drain.configure(bg="light slate gray")
Button_drain.configure(text='''Drain''', height="2", width="16",
                       command=lambda: threading.Thread(name = "drainSpin",
                                                        target = spinToLocation,
                                                        args = [drainTime]).start())

Button_bottom = tk.Button()
Button_bottom.grid(row=2, column=1, padx=(25,25), pady=(10,10))
Button_bottom.configure(bg="light slate gray")
Button_bottom.configure(text='''Bottom''', height="2", width="16",
                        command=lambda: threading.Thread(name = "bottomSpin",
                                                         target = spinToLocation,
                                                         args = [bottomTime]).start())

Entry_bar = tk.Entry(width="4")
Entry_bar.grid(row=0, column=2)

Button_setToBar = tk.Button()
Button_setToBar.grid(row=1, column=2, padx=(25,25), pady=(10,10))
Button_setToBar.configure(bg="light slate gray")
Button_setToBar.configure(text='''Set To BAR''', height="2", width="16",
                          command=lambda: threading.Thread(name="setBar", target=setToBar_thread).start())

Button_vacuum = tk.Button()
Button_vacuum.grid(row=2, column=2, padx=(25,25), pady=(10,10))
Button_vacuum.configure(bg="light slate gray")
Button_vacuum.configure(text='''Vacuum''', height="2", width="16",
                        command=lambda: Pressure.deflate())

Button_pressure = tk.Button()
Button_pressure.grid(row=3, column=2, padx=(25,25), pady=(10,10))
Button_pressure.configure(bg="light slate gray")
Button_pressure.configure(text='''Pressure''', height="2", width="16",
                          command=lambda: Pressure.inflate())

Button_emergency = tk.Button()
Button_emergency.grid(row=3, column=0, columnspan=2, padx=(25,25), pady=(10,10))
Button_emergency.configure(activebackground="#ededed")
Button_emergency.configure(background="#d81125")
Button_emergency.configure(text='''EMERGENCY STOP!''', height="2", width="42",
                           command=lambda: emergencyStop())

Button_programOne = tk.Button()
Button_programOne.grid(row=0, column=3, padx=(25,25), pady=(10,10))
Button_programOne.configure(bg="light slate gray")
Button_programOne.configure(text='''White''', height="2", width="16",
                            command=lambda: pressProgram("White" , programs[0]).start())

Button_programTwo = tk.Button()
Button_programTwo.grid(row=1, column=3, padx=(25,25), pady=(10,10))
Button_programTwo.configure(bg="light slate gray")
Button_programTwo.configure(text='''Red''', height="2", width="16",
                             command=lambda: pressProgram("Red" , programs[1]).start())

Button_programThree = tk.Button()
Button_programThree.grid(row=2, column=3, padx=(25,25), pady=(10,10))
Button_programThree.configure(bg="light slate gray")
Button_programThree.configure(text='''Custom''', height="2", width="16",
                              command=lambda: pressProgram("Custom", programs[2]).start())


Button_editor = tk.Button()
Button_editor.grid(row=3, column=3, padx=(25,25), pady=(10,10))
Button_editor.configure(text='''Editor''', height="2", width="16", bg="light slate gray",
                        command=lambda: open_editor())

bar_gauge = tk.Label(root, 
                           text="0.00 BAR", 
                           font=("Courier", 48, "bold"), 
                           bg="black", 
                           fg="lime green", 
                           width=10, 
                           relief="ridge", 
                           bd=10)
bar_gauge.grid(row=4, column=0, columnspan=2, pady=20)

text_box = ScrolledText.ScrolledText() #console
text_box.configure(background="#000000", foreground="#08ff31", wrap="word")
text_box.configure(height=8, width=42)
text_box.grid(row=4, column=2, columnspan=2, pady=10)
text_box.insert(tk.INSERT, "Lo-Fi Wines - Wine Press 2020\n")

lbl = tk.Label()  #clock
lbl.grid(row=0, column=0)
lbl.configure(bg="SteelBlue3")

# ----------------------Graphing------------
style.use('dark_background')

x_len = 1000
y_range = [-0.5, 2]
fig = plt.figure()
# gs = fig.add_gridspec(3,3)
ax = fig.add_subplot(1, 1, 1)
ax.grid(linestyle='-', linewidth='0.5', color='gray')

ax.set_title("BAR / time")
xs = list(range(0, 1000))
ys = [0] * x_len
ax.set_ylim(y_range)
line, = ax.plot(xs, ys)

def animate(i, ys):
    ys.append(pressure_data)
    ys = ys[-x_len:]
    line.set_ydata(ys)
    return line,

canvas = FigureCanvasTkAgg(fig, root)  #graph
canvas.get_tk_widget().configure(height=200, width=1300)
canvas.get_tk_widget().grid(row=5, column=0, columnspan=4)

# -------------------Emergency Stop------------------------
def emergencyStop():
    #pdb.set_trace()
    global spinning_flag, pressure_flag, count, emerg_flag, program_flag
    GPIO.output(pinList, GPIO.HIGH)
    spinning_flag = 0
    pressure_flag = 0
    emerg_flag = 1
    program_flag = 0
    count = 0
    printBox("EMERGENCY STOP")
    if len(threading.enumerate()) > 1:
        iterThreads = threading.enumerate()
        for thread in iterThreads:
            name = str(thread.getName())
            print(name)
            if(thread.isAlive()) and name not in ["MainThread", "setBar",
                                                  "bottomSpin", "topSpin", "drainSpin"] and "Thread" not in name:
                print("alive- " + name)
                thread.raise_exception()
                thread.join()
                print("dead?")

    Button_left.configure(bg="light slate gray")
    Button_right.configure(bg="light slate gray")
    Button_vacuum.configure(bg="light slate gray")
    Button_pressure.configure(bg="light slate gray")
    Button_top.configure(bg="light slate gray")
    Button_drain.configure(bg="light slate gray")
    Button_bottom.configure(bg="light slate gray")
    Button_programOne.configure(bg="light slate gray")
    Button_programTwo.configure(bg="light slate gray")
    Button_programThree.configure(bg="light slate gray")
    time.sleep(1)
    emerg_flag = 0



# ---------------------------------MAIN------
if __name__ == '__main__':
    threading.Thread(target=pressure_updater, daemon=True).start()
    ani = animation.FuncAnimation(fig, animate, fargs=(ys,), interval=200, blit=True)
    update_gauge()
    myTime()
    root.mainloop()
    print("GUI initialized and running.")