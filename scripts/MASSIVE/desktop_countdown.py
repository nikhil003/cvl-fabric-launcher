# Simple GUI which shows remaining walltime of desktop

import Tkinter as tk
import os
import subprocess
from subprocess import call


class DesktopCountdownApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.label = tk.Label(self, text="", width=40)
        self.label.pack()
        self.remaining = 0
        self.countdown()
        self.wm_title("Walltime remaining")
        # self.label = tk.Label("Walltime Remaining")
        # self.label.pack()

    def countdown(self):
        timeleft="unknown"
        jobid=os.path.expandvars("$SLURM_JOBID")
        cmd=["squeue","--noheader","--jobs=" + jobid,"--format='%L"]
        p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            timeleft = line

        self.label.configure(text="Time left: " + timeleft)
        self.remaining = self.remaining - 1
        self.after(10000, self.countdown)

if __name__ == "__main__":
    app = DesktopCountdownApp()
    app.mainloop()
