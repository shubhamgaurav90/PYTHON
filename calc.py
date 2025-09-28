# super_calculator.py
import tkinter as tk
from tkinter import ttk, messagebox
import math
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


history_list = []       # stores "expr = result"
memory_value = 0.0      # memory register
MAX_HISTORY = 20


SAFE_ENV = {"__builtins__": None}

THEMES = {
    "Dark": {
        "bg": "#1e1e2f", "fg": "white",
        "entry_bg": "#2d2d44", "btn_bg": "#3c3f58", "accent": "#5df0c1"
    },
    "Light": {
        "bg": "#f2f2f2", "fg": "black",
        "entry_bg": "white", "btn_bg": "#e0e0e0", "accent": "#007acc"
    },
    "Neon": {
        "bg": "#0b0f1a", "fg": "#e8fffb",
        "entry_bg": "#07101a", "btn_bg": "#0e2541", "accent": "#39ff14"
    },
    "Classic": {
        "bg": "#ece6d6", "fg": "#1a1a1a",
        "entry_bg": "white", "btn_bg": "#d4c9a5", "accent": "#c94234"
    }
}
current_theme_name = "Dark"

# --------- Helper functions ----------
def math_env():
    env = {}
    env.update(math.__dict__)       # bring math functions/constants
    # Add numpy aliases sometimes needed (e.g., np.pi not allowed, but math.pi available)
    # Provide safe 'abs', 'round' etc. (math has them)
    return env

def safe_eval(expr, extra_vars=None):
    """
    Evaluate math expression safely with math module functions only.
    extra_vars: dict of additional variables (like {'x': 2})
    """
    env = math_env()
    if extra_vars:
        env.update(extra_vars)
    try:
        return eval(expr, SAFE_ENV, env)
    except Exception as e:
        raise

# --------- Theme application ----------
def apply_theme(theme_name):
    global current_theme_name
    current_theme_name = theme_name
    th = THEMES[theme_name]
    root.configure(bg=th["bg"])
    style.configure("TFrame", background=th["bg"])
    style.configure("TLabel", background=th["bg"], foreground=th["fg"])
    style.configure("TButton", background=th["btn_bg"], foreground=th["fg"])
    # Calculator widgets
    entry.config(bg=th["entry_bg"], fg=th["fg"], insertbackground=th["fg"])
    status_label.config(bg=th["bg"], fg=th["fg"])
    history_listbox.config(bg=th["entry_bg"], fg=th["fg"])
    for btn in calc_buttons:
        btn.config(bg=th["btn_bg"], fg=th["fg"], activebackground=th["accent"])
    # Converter
    conv_frame.config(bg=th["bg"])
    for w in conv_frame.winfo_children():
        try:
            w.config(bg=th["bg"], fg=th["fg"])
        except:
            pass
    # Graph frame
    graph_panel.config(bg=th["bg"])
    # Settings widgets colors
    settings_frame.config(bg=th["bg"])
    for w in settings_frame.winfo_children():
        try:
            w.config(bg=th["bg"], fg=th["fg"])
        except:
            pass

# --------- Calculator logic ----------
def press_key(key):
    if key == "=":
        evaluate_expression()
    elif key == "C":
        entry.delete(0, tk.END)
        status_label.config(text="Ready")
    elif key == "DEL":
        s = entry.get()
        entry.delete(0, tk.END)
        entry.insert(0, s[:-1])
    elif key in ("M+", "M-", "MR", "MC"):
        handle_memory(key)
    else:
        entry.insert(tk.END, key)

def evaluate_expression():
    expr = entry.get().strip()
    if not expr:
        return
    # replace ^ with **
    expr_safe = expr.replace("^", "**")
    # handle plot call inside calculator - redirect to graph tab
    if expr_safe.startswith("plot(") and expr_safe.endswith(")"):
        notebook.select(graph_tab)
        graph_input.delete(0, tk.END)
        graph_input.insert(0, expr_safe)
        plot_from_input()
        return

    try:
        res = safe_eval(expr_safe)
        entry.delete(0, tk.END)
        entry.insert(0, str(res))
        add_history(f"{expr} = {res}")
        status_label.config(text=f"Last Answer: {res}")
    except Exception as e:
        entry.delete(0, tk.END)
        entry.insert(0, "Error")
        status_label.config(text=f"Error: {e}")

def add_history(item):
    history_list.append(item)
    if len(history_list) > MAX_HISTORY:
        history_list.pop(0)
    refresh_history_box()

def refresh_history_box():
    history_listbox.delete(0, tk.END)
    for it in reversed(history_list):
        history_listbox.insert(tk.END, it)

def on_history_double(event):
    sel = None
    try:
        sel = history_listbox.get(history_listbox.curselection())
    except:
        return
    expr = sel.split("=")[0].strip()
    entry.delete(0, tk.END)
    entry.insert(0, expr)
    status_label.config(text=f"Reused: {expr}")

# --------- Memory ----------
def handle_memory(cmd):
    global memory_value
    try:
        if cmd == "M+":
            val = float(entry.get())
            memory_value += val
            status_label.config(text=f"Memory: {memory_value}")
        elif cmd == "M-":
            val = float(entry.get())
            memory_value -= val
            status_label.config(text=f"Memory: {memory_value}")
        elif cmd == "MR":
            entry.insert(tk.END, str(memory_value))
            status_label.config(text=f"Recalled Memory: {memory_value}")
        elif cmd == "MC":
            memory_value = 0.0
            status_label.config(text="Memory cleared")
    except Exception:
        status_label.config(text="Memory Error")

# --------- Graph plotting ----------
def plot_from_input():
    expr = graph_input.get().strip()
    if not expr:
        return
    # Accept plot(func) or plot(func, xmin, xmax)
    if not (expr.startswith("plot(") and expr.endswith(")")):
        messagebox.showerror("Plot error", "Plot input must be of form: plot(expr) or plot(expr, xmin, xmax)")
        return
    inner = expr[5:-1]  # remove plot( )
    parts = split_args(inner)
    func_part = parts[0]
    try:
        if len(parts) == 1:
            xmin, xmax = -10, 10
        elif len(parts) >= 3:
            xmin = float(safe_eval(parts[1]))
            xmax = float(safe_eval(parts[2]))
        else:
            # maybe provided only xmin or only xmax - fallback
            xmin, xmax = -10, 10

        x = np.linspace(xmin, xmax, 400)
        y = []
        for xv in x:
            try:
                yv = safe_eval(func_part, {"x": xv})
                y.append(yv)
            except Exception:
                y.append(np.nan)

        # clear figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(x, y, label=func_part)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"Plot: {func_part}")
        ax.grid(True)
        ax.legend()
        canvas.draw()
        status_label.config(text=f"Plotted: {func_part}")
    except Exception as e:
        messagebox.showerror("Plotting error", str(e))
        status_label.config(text=f"Plot Error: {e}")

def split_args(s):
    # split by commas, but allow nested parentheses in func expression
    args = []
    depth = 0
    cur = ""
    for ch in s:
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
    if cur.strip():
        args.append(cur.strip())
    return args

# --------- Unit converter ----------
def open_converter_tab():
    notebook.select(converter_tab)

def convert_unit():
    opt = conv_option.get()
    val_s = conv_entry.get().strip()
    if not val_s:
        conv_result_var.set("Enter value")
        return
    try:
        val = float(val_s)
    except:
        conv_result_var.set("Invalid number")
        return

    if opt == "Length: m → cm":
        res = val * 100
        conv_result_var.set(f"{res} cm")
    elif opt == "Length: cm → m":
        res = val / 100
        conv_result_var.set(f"{res} m")
    elif opt == "Weight: kg → g":
        res = val * 1000
        conv_result_var.set(f"{res} g")
    elif opt == "Weight: g → kg":
        res = val / 1000
        conv_result_var.set(f"{res} kg")
    elif opt == "Temp: C → F":
        res = (val * 9/5) + 32
        conv_result_var.set(f"{res} °F")
    elif opt == "Temp: F → C":
        res = (val - 32) * 5/9
        conv_result_var.set(f"{res} °C")
    else:
        conv_result_var.set("Option not supported")

# --------- UI Construction ----------
root = tk.Tk()
root.title("All-in-One Scientific Calculator")
root.geometry("1000x700")
root.minsize(900, 600)

style = ttk.Style(root)
style.theme_use('default')
style.configure("TNotebook", background=THEMES[current_theme_name]["bg"])
style.configure("TNotebook.Tab", padding=[10, 6])

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=8, pady=8)

# ---- Calculator Tab ----
calc_tab = ttk.Frame(notebook)
notebook.add(calc_tab, text="Calculator")

# top frame for entry + history
top_frame = tk.Frame(calc_tab)
top_frame.pack(fill="x", padx=8, pady=6)

entry = tk.Entry(top_frame, font=("Consolas", 20), justify="right", bd=6, relief="sunken")
entry.pack(side="left", fill="x", expand=True, padx=(0,10), ipady=6)

# Right frame: history & memory label
right_frame = tk.Frame(top_frame, width=260)
right_frame.pack(side="right", fill="y")

hist_label = tk.Label(right_frame, text="History", font=("Consolas", 12, "bold"))
hist_label.pack(anchor="nw")

history_listbox = tk.Listbox(right_frame, width=36, height=10, font=("Consolas", 11))
history_listbox.pack(fill="y", expand=True)
history_listbox.bind("<Double-1>", on_history_double)

mem_frame = tk.Frame(right_frame)
mem_frame.pack(fill="x", pady=6)
tk.Button(mem_frame, text="M+", width=6, command=lambda: handle_memory("M+")).pack(side="left", padx=3)
tk.Button(mem_frame, text="M-", width=6, command=lambda: handle_memory("M-")).pack(side="left", padx=3)
tk.Button(mem_frame, text="MR", width=6, command=lambda: handle_memory("MR")).pack(side="left", padx=3)
tk.Button(mem_frame, text="MC", width=6, command=lambda: handle_memory("MC")).pack(side="left", padx=3)

# buttons frame
buttons_frame = tk.Frame(calc_tab)
buttons_frame.pack(fill="both", expand=True, padx=8, pady=6)

calc_button_texts = [
    ["7","8","9","/","C"],
    ["4","5","6","*","^"],
    ["1","2","3","-","sqrt("],
    ["0",".","(",")","+"],
    ["sin(","cos(","tan(","log(","="],
    ["pi","e","exp(","factorial(","DEL"]
]

calc_buttons = []
for r, row in enumerate(calc_button_texts):
    for c, txt in enumerate(row):
        b = tk.Button(buttons_frame, text=txt, width=10, height=2,
                      font=("Consolas", 12), command=lambda t=txt: press_key(t))
        b.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
        calc_buttons.append(b)

# make grid expand nicely
for i in range(len(calc_button_texts)):
    buttons_frame.grid_rowconfigure(i, weight=1)
for j in range(5):
    buttons_frame.grid_columnconfigure(j, weight=1)

# Status bar
status_label = tk.Label(root, text="Ready", anchor="w", font=("Consolas", 11))
status_label.pack(fill="x", padx=8, pady=(0,6))

# ---- Converter Tab ----
converter_tab = ttk.Frame(notebook)
notebook.add(converter_tab, text="Converter")

conv_frame = tk.Frame(converter_tab)
conv_frame.pack(fill="both", expand=True, padx=12, pady=10)

tk.Label(conv_frame, text="Unit Converter", font=("Consolas", 16, "bold")).pack(pady=6)

conv_option = tk.StringVar(conv_frame)
conv_option.set("Length: m → cm")
conv_menu = ttk.OptionMenu(conv_frame, conv_option,
                           conv_option.get(),
                           "Length: m → cm", "Length: cm → m",
                           "Weight: kg → g", "Weight: g → kg",
                           "Temp: C → F", "Temp: F → C")
conv_menu.pack(pady=8)

conv_entry = tk.Entry(conv_frame, font=("Consolas", 14))
conv_entry.pack(pady=6)

conv_btn = tk.Button(conv_frame, text="Convert", font=("Consolas", 12, "bold"),
                     command=convert_unit)
conv_btn.pack(pady=6)

conv_result_var = tk.StringVar(value="")
conv_result_label = tk.Label(conv_frame, textvariable=conv_result_var, font=("Consolas", 14, "bold"))
conv_result_label.pack(pady=6)

# ---- Graph Tab ----
graph_tab = ttk.Frame(notebook)
notebook.add(graph_tab, text="Graph")

graph_panel = tk.Frame(graph_tab)
graph_panel.pack(fill="both", expand=True, padx=8, pady=8)

# input area for plot
graph_input_frame = tk.Frame(graph_panel)
graph_input_frame.pack(fill="x", padx=6, pady=6)
tk.Label(graph_input_frame, text="Plot command:", font=("Consolas", 12)).pack(side="left")
graph_input = tk.Entry(graph_input_frame, font=("Consolas", 12))
graph_input.pack(side="left", fill="x", expand=True, padx=6)
graph_input.insert(0, "plot(sin(x), -6.28, 6.28)")
tk.Button(graph_input_frame, text="Plot", command=plot_from_input).pack(side="left", padx=6)

# matplotlib figure
fig = Figure(figsize=(6,4), dpi=100)
ax = fig.add_subplot(111)
ax.grid(True)
canvas = FigureCanvasTkAgg(fig, master=graph_panel)
canvas.get_tk_widget().pack(fill="both", expand=True)
canvas.draw()

# ---- Settings Tab ----
settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

settings_frame = tk.Frame(settings_tab)
settings_frame.pack(fill="both", expand=True, padx=12, pady=12)

tk.Label(settings_frame, text="Theme", font=("Consolas", 14, "bold")).pack(anchor="w", pady=6)
theme_var = tk.StringVar(value=current_theme_name)
for name in THEMES.keys():
    rb = tk.Radiobutton(settings_frame, text=name, variable=theme_var, value=name,
                        command=lambda n=name: apply_theme(n), font=("Consolas", 12))
    rb.pack(anchor="w")

# quick tips
tk.Label(settings_frame, text="\nQuick Tips:", font=("Consolas", 12, "bold")).pack(anchor="w", pady=(10,2))
tk.Label(settings_frame, text="- Use '^' for power (2^3 = 8)\n- Use factorial(n) for n!\n- Use plot(expr, xmin, xmax) to graph\n- Double-click history to reuse",
         justify="left", font=("Consolas", 11)).pack(anchor="w")

# ---- Wire up initial theme and other small bindings ----
apply_theme(current_theme_name)
refresh_history_box()

# allow Enter key to evaluate in calculator entry
entry.bind("<Return>", lambda e: evaluate_expression())

# menu: give ability to jump to sections quickly
menubar = tk.Menu(root)
root.config(menu=menubar)
nav_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Navigate", menu=nav_menu)
nav_menu.add_command(label="Calculator", command=lambda: notebook.select(calc_tab))
nav_menu.add_command(label="Converter", command=lambda: notebook.select(converter_tab))
nav_menu.add_command(label="Graph", command=lambda: notebook.select(graph_tab))
nav_menu.add_command(label="Settings", command=lambda: notebook.select(settings_tab))

# finish
root.mainloop()