#!/usr/bin/env python3
# Yves Piguet, February-March 2021

import sys
import tkinter as tk

from tdmclient import ClientAsync


class VariableTableWindow(tk.Tk):

    def __init__(self):
        super(VariableTableWindow, self).__init__()
        self.geometry("600x420")
        self.title("No robot")

        # menus
        accelerator_key = "Cmd" if sys.platform == "darwin" else "Ctrl"
        bind_key = "Command" if sys.platform == "darwin" else "Control"
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.bind("<" + bind_key + "-q>", lambda event: self.quit())

        if sys.platform != "darwin":
            file_menu = tk.Menu(menubar, tearoff=False)
            file_menu.add_command(
                label="Quit",
                command=self.quit,
                accelerator=accelerator_key+"-Q"
            )
            menubar.add_cascade(label="File", menu=file_menu)

        robot_menu = tk.Menu(menubar, tearoff=False)
        lock_node_var = tk.BooleanVar()
        robot_menu.add_checkbutton(
            label="Control",
            variable=lock_node_var,
            accelerator=accelerator_key+"-L"
        )
        self.bind("<" + bind_key + "-l>", lambda event: lock_node_var.set(not lock_node_var.get()))
        lock_node_var.trace_add("write",
                                lambda var, index, mode: self.lock_node(lock_node_var.get()))
        menubar.add_cascade(label="Robot", menu=robot_menu)

        # main layout: info at top (one line), scrollable variables below
        self.main_content = tk.Frame(self)
        self.main_content.pack(fill=tk.BOTH, expand=True)
        self.info_line = tk.Label(self, anchor="w", bg="#fff", fg="#666", height=1) # 1 char unit
        self.info_line.pack(side=tk.BOTTOM, fill=tk.X)

        # variables
        self.canvas = None
        self.scrollbar = None
        self.frame = None

        # key=name, value={"widget": w, "value": v}
        self.variables = {}

        self.edited_variable = None

        self.client = None
        self.node = None
        self.node_id_str = None

        self.start_co = None

    async def prog(self):
        await self.client.wait_for_status(self.client.NODE_STATUS_AVAILABLE)
        self.node = self.client.first_node()
        self.node_id_str = self.node["node_id_str"]
        name = self.node["name"]
        if self.client.tdm_addr is not None:
            name += f" (TDM: {self.client.tdm_addr}:{self.client.tdm_port})"
        self.title(name)
        await self.client.watch(self.node_id_str, variables=True)

    def lock_node(self, locked):
        if locked:
            self.client.send_lock_node(self.node_id_str)
        else:
            self.client.send_unlock_node(self.node_id_str)

    def add_variable(self, name, value):
        if value is not None:
            text = ", ".join([str(item) for item in value])
            if name not in self.variables:
                if self.frame is None:
                    self.canvas = tk.Canvas(self.main_content)
                    self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
                    self.scrollbar = tk.Scrollbar(self.main_content, orient="vertical", command=self.canvas.yview)
                    self.scrollbar.pack(side=tk.RIGHT, fill="y")
                    self.canvas.configure(yscrollcommand=self.scrollbar.set)
                    self.canvas.bind("<Configure>",
                                    lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
                    self.canvas.bind("<Enter>",
                                     lambda event: self.canvas.bind_all("<MouseWheel>",
                                                                        lambda event: self.canvas.yview_scroll(-event.delta // 120, "units")))
                    self.canvas.bind("<Leave>",
                                     lambda event: self.canvas.unbind_all("<MouseWheel>"))
                    self.frame = tk.Frame(self.canvas)
                    self.frame.bind("<Configure>",
                                    lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
                    self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
                f = tk.Frame(self.frame)
                f.pack(fill=tk.X, expand=True)
                title = name + (f"[{len(value)}]" if len(value) > 1 else "")
                l = tk.Label(f, text=title, anchor="w", width=25)
                l.pack(side=tk.LEFT)
                v = tk.Label(f, text=text, anchor="w")
                v.pack(side=tk.LEFT, fill=tk.X, expand=True)
                v.bind("<Button-1>",
                    lambda e: self.begin_editing(name))
                self.variables[name] = {
                    "widget": f,
                    "vwidget": v,
                    "ewidget": None,
                    "value": value,
                    "text": text,
                }
            else:
                v = self.variables[name]
                v["text"] = text
                v["vwidget"]["text"] = text

    def clear_variables(self):
        self.end_editing(cancel=True)
        for name in self.variables:
            self.variables[name]["widget"].destroy()
        self.variables = {}
        if self.canvas is not None:
            self.canvas.destroy()
            self.canvas = None
            self.frame = None
            self.scrollbar.destroy()
            self.scrollbar = None

    def begin_editing(self, name):
        if self.node["status"] != self.client.NODE_STATUS_READY or not self.end_editing(keep_editing_on_error=True):
            return
        self.edited_variable = name
        v = self.variables[name]
        entry = tk.Entry(v["vwidget"])
        v["ewidget"] = entry
        entry.insert(0, v["text"])
        entry.place(x=0, y=0, anchor="nw", relwidth=1, relheight=1)
        entry.bind("<Return>", lambda e: self.end_editing(keep_editing_on_error=True))
        entry.bind("<Escape>", lambda e: self.end_editing(cancel=True))
        entry.focus_set()

    def end_editing(self, cancel=False, keep_editing_on_error=False):
        if self.edited_variable is not None:
            v = self.variables[self.edited_variable]
            text = v["ewidget"].get()
            if not cancel:
                try:
                    new_value = [int(s) for s in text.split(",")]
                    if len(new_value) != len(v["value"]):
                        raise Exception()
                    self.client.send_set_variables(self.node_id_str, {self.edited_variable: new_value})
                except Exception as e:
                    print(type(e), e)
                    if keep_editing_on_error:
                        return False
            v["ewidget"].destroy()
            v["ewidget"] = None
            self.edited_variable = None
        return True

    def connect(self):

        def on_nodes_changed(nodes):
            self.node = (nodes[0]
                         if len(nodes) > 0 and nodes[0]["status"] != self.client.NODE_STATUS_DISCONNECTED
                         else None)
            if self.node is None:
                self.node_id_str = None
                self.clear_variables()
                self.title("No robot")
                self.info_line["text"] = ""
            else:
                self.info_line["text"] = {
                    self.client.NODE_STATUS_UNKNOWN: "No robot",
                    self.client.NODE_STATUS_CONNECTED: "Robot connected",
                    self.client.NODE_STATUS_AVAILABLE: "Observe",
                    self.client.NODE_STATUS_BUSY: "Observe (robot busy)",
                    self.client.NODE_STATUS_READY: "Control",
                    self.client.NODE_STATUS_DISCONNECTED: "Robot disconnected",
                }[self.node["status"]]
                if self.node_id_str is None:
                    # new node, set it up by starting coroutine
                    self.start_co = self.prog()

        def on_variables_changed(node_id_str, data):
            if self.edited_variable is None:
                variables = data["variables"]
                for name in variables:
                    self.add_variable(name, variables[name])

        self.client = ClientAsync()
        self.client.on_nodes_changed = on_nodes_changed
        self.client.on_variables_changed = on_variables_changed
        # schedule communication
        self.after(100, self.run)

    def run(self):
        if self.start_co is not None:
            if not self.client.step_coroutine(self.start_co):
                # start_co is finished
                self.start_co = None
        else:
            self.client.process_waiting_messages()
        self.after(100, self.run)


if __name__ == "__main__":

    win = VariableTableWindow()
    win.connect()
    win.mainloop()
