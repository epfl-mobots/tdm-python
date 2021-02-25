#!/usr/bin/env python3
# Yves Piguet, Feb 2021

import sys
import os
import tkinter as tk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from tdmclient import ClientAsync


class VariableTableWindow(tk.Tk):

    def __init__(self):
        super(VariableTableWindow, self).__init__()
        self.geometry("600x420")

        self.canvas = tk.Canvas(self)
        self.canvas.pack(side=tk.LEFT, fill="y")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>",
                         lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.frame = tk.Frame(self.canvas)
        self.frame.bind("<Configure>",
                        lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        # key=name, value={"widget": w, "value": v}
        self.variables = {}

        self.client = None
        self.node_id_str = None

        async def prog():
            await self.client.wait_for_status(self.client.NODE_STATUS_AVAILABLE)
            node = self.client.first_node()
            self.node_id_str = node["node_id_str"]
            name = node["name"]
            self.title(name)
            await self.client.lock_node(self.node_id_str)
            await self.client.wait_for_status(self.client.NODE_STATUS_READY)
            await self.client.watch(self.node_id_str)

        # start coroutine, set to None once finished
        # (then will continue handling incoming messages forever)
        self.start_co = prog()

    def add_variable(self, name, value):
        if name not in self.variables:
            f = tk.Frame(self.frame)
            f.pack(fill=tk.X)
            l = tk.Label(f, text = name, anchor="w", width=20)
            l.pack(side=tk.LEFT)
            v = tk.Label(f, text = str(value), anchor="w")
            v.pack(side=tk.LEFT)
            self.variables[name] = {
                "widget": f,
                "vwidget": v,
                "value": value
            }
        else:
            v = self.variables[name]
            v["vwidget"]["text"] = str(value)

    def clear_variables(self):
        for name in self.variables:
            self.variables[name]["widget"].destroy()
        self.variables = {}

    def connect(self):

        def on_variables_changed(node_id_str, data):
            variables = data["variables"]
            for i, v in enumerate(variables):
                self.add_variable(v["name"], v["value"])

        self.client = ClientAsync()
        self.client.on_variables_changed = on_variables_changed
        # schedule communication
        self.after(100, self.run)

    def run(self):
        if self.start_co is not None:
            if not self.client.step_async_program(self.start_co):
                # start_co is finished
                self.start_co = None
        else:
            self.client.process_waiting_messages()
        self.after(100, self.run)


if __name__ == "__main__":

    win = VariableTableWindow()
    win.connect()
    win.mainloop()
