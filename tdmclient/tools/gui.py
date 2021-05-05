# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import getopt
import tkinter as tk
import tkinter.filedialog as filedialog

from tdmclient import ClientAsync
from tdmclient.atranspiler import ATranspiler


class VariableTableWindow(tk.Tk):

    def __init__(self, tdm_addr=None, tdm_port=None, language=None, debug=0):
        super(VariableTableWindow, self).__init__()
        self.geometry("800x600")

        self.program_path = None
        self.program_src = ""
        self.language = language or "aseba"
        self.tdm_addr = tdm_addr
        self.tdm_port = tdm_port
        self.debug = debug

        # menus
        accelerator_key = "Cmd" if sys.platform == "darwin" else "Ctrl"
        bind_key = "Command" if sys.platform == "darwin" else "Control"
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.bind("<" + bind_key + "-q>", lambda event: self.quit())

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="New",
            command=self.new,
            accelerator=accelerator_key+"-N"
        )
        self.bind("<" + bind_key + "-n>", lambda event: self.new())
        file_menu.add_separator()
        file_menu.add_command(
            label="Open",
            command=self.open,
            accelerator=accelerator_key+"-O"
        )
        self.bind("<" + bind_key + "-o>", lambda event: self.open())
        file_menu.add_command(
            label="Save",
            command=lambda: self.save(self.program_path),
            accelerator=accelerator_key+"-S"
        )
        self.bind("<" + bind_key + "-s>", lambda event: self.save(self.program_path))
        file_menu.add_command(
            label="Save As...",
            command=lambda: self.save(None),
            accelerator=accelerator_key+"-Shift-"
        )
        self.bind("<" + bind_key + "-S>", lambda event: self.save(None))
        if sys.platform != "darwin":
            file_menu.add_separator()
            file_menu.add_command(
                label="Quit",
                command=self.quit,
                accelerator=accelerator_key+"-Q"
            )
        menubar.add_cascade(label="File", menu=file_menu)

        def send_event_to_focused_widget(event_id):
            widget = self.focus_get()
            if widget is not None:
                widget.event_generate(event_id)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(
            label="Cut",
            command=lambda: send_event_to_focused_widget("<<Cut>>")
        )
        edit_menu.add_command(
            label="Copy",
            command=lambda: send_event_to_focused_widget("<<Copy>>")
        )
        edit_menu.add_command(
            label="Paste",
            command=lambda: send_event_to_focused_widget("<<Paste>>")
        )
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        self.view_var = tk.IntVar()
        view_menu.add_radiobutton(
            label="Variables",
            variable=self.view_var,
            value=1,
            command=self.set_view_variables,
            accelerator=accelerator_key+"-Shift-V"
        )
        self.bind("<" + bind_key + "-V>", lambda event: self.set_view_variables())
        view_menu.add_radiobutton(
            label="Program",
            variable=self.view_var,
            value=2,
            command=self.set_view_program,
            accelerator=accelerator_key+"-Shift-P"
        )
        self.bind("<" + bind_key + "-P>", lambda event: self.set_view_program())
        menubar.add_cascade(label="View", menu=view_menu)
        self.view_var.set(1)

        self.robot_menu = tk.Menu(menubar, tearoff=False)
        lock_node_var = tk.BooleanVar()
        self.robot_menu.add_checkbutton(
            label="Control",
            variable=lock_node_var,
            accelerator=accelerator_key+"-L"
        )
        self.bind("<" + bind_key + "-l>", lambda event: lock_node_var.set(not lock_node_var.get()))
        lock_node_var.trace_add("write",
                                lambda var, index, mode: self.lock_node(lock_node_var.get()))
        self.robot_menu.add_separator()
        self.robot_menu.add_command(
            label="Run",
            command=self.run_program,
            state="disabled",
            accelerator=accelerator_key+"-R"
        )
        self.bind("<" + bind_key + "-r>", lambda event: self.run_program())
        self.robot_menu.add_command(
            label="Stop",
            command=self.stop_program,
            state="disabled",
            accelerator="Escape"
        )
        self.bind("<Escape>", lambda event: self.stop_program())
        self.robot_menu.add_separator()
        self.language_var = tk.IntVar()
        self.robot_menu.add_radiobutton(
            label="Aseba",
            variable=self.language_var,
            value=1,
            command=lambda: self.set_language("aseba")
        )
        self.robot_menu.add_radiobutton(
            label="Python",
            variable=self.language_var,
            value=2,
            command=lambda: self.set_language("py")
        )
        self.language_var.set(1)
        menubar.add_cascade(label="Robot", menu=self.robot_menu)

        # main layout: info at bottom (one line), scrollable main content above
        self.main_content = tk.Frame(self)
        self.main_content.pack(fill=tk.BOTH, expand=True)
        status_frame = tk.Frame(self, height=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.info_mode = tk.Label(status_frame, anchor="w", bg="#fff", fg="#666", width=16)  # char units
        self.info_mode.pack(side=tk.LEFT)
        self.info_error = tk.Label(status_frame, anchor="e", bg="#fff", fg="#666")
        self.info_error.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # variables
        self.canvas = None
        self.scrollbar = None
        self.frame = None

        # program
        self.text_program = None

        # key=name, value={"widget": w, "value": v}
        self.variables = {}

        self.edited_variable = None

        self.client = None
        self.node = None
        self.locked = False

        self.start_co = None

        self.set_title()

    def set_title(self):
        name = self.node.props["name"] if self.node is not None else "No robot"
        if self.client is not None and self.client.tdm_addr is not None:
            name += f" (TDM: {self.client.tdm_addr}:{self.client.tdm_port})"
        if self.text_program is not None:
            name += " - "
            name += os.path.basename(self.program_path) if self.program_path is not None else f"Untitled.{self.language}"
        self.title(name)

    def set_view_variables(self):
        self.view_var.set(1)
        self.remove_program_view()
        self.create_variable_view()
        self.set_title()

    def set_view_program(self):
        self.view_var.set(2)
        self.remove_variable_view()
        self.create_program_view()
        self.set_title()

    def set_language(self, language):
        self.language_var.set({
            "aseba": 1,
            "py": 2,
        }[language])
        self.language = language
        self.set_title()

    def new(self):
        self.remove_program_view()
        self.program_src = ""
        self.program_path = None
        self.set_view_program()

    def open(self):
        path = filedialog.askopenfilename(filetypes=[("All",".aseba .py"),
                                                     ("Aseba", ".aseba"),
                                                     ("Python", ".py")])
        if path:
            with open(path, encoding="utf-8") as f:
                self.remove_program_view()
                self.program_src = f.read()
                self.program_path = path
                self.set_view_program()
                self.text_program.edit_modified(False)
                self.set_language("py"
                                  if os.path.splitext(path)[1] == ".py"
                                  else "aseba")

    def save(self, path):
        if path is None:
            path = filedialog.asksaveasfilename(filetypes=[("Aseba", ".aseba"),],
                                                defaultextension = "." + self.language)
        if path:
            with open(path, "wb") as f:
                self.program_src = self.text_program.get("1.0", "end")
                f.write(bytes(self.program_src, "utf-8"))
                self.text_program.edit_modified(False)
                self.program_path = path

    def run_src(self, src_aseba):

        async def run_a():
            error = await self.node.compile(src_aseba)
            if error is not None:
                self.error_msg = error["error_msg"]
                self.info_error["text"] = self.error_msg
            else:
                error = await self.node.run()
                if error is not None:
                    self.error_msg = f"Run error {error['error_code']}"
                    self.info_error["text"] = self.error_msg
                else:
                    self.error_msg = None
                    self.info_error["text"] = "OK"

        self.client.run_async_program(run_a)

    def run_program(self):
        if self.locked and self.text_program is not None:
            self.program_src = self.text_program.get("1.0", "end")
            if self.language == "py":
                try:
                    aseba_src = ATranspiler.simple_transpile(self.program_src)
                except Exception as e:
                    self.error_msg = str(e)
                    self.info_error["text"] = self.error_msg
                    return
            else:
                aseba_src = self.program_src
            self.run_src(aseba_src)

    def stop_program(self):

        async def stop_a():
            error = await self.node.stop()
            if error is not None:
                self.error_msg = f"Stop error {error['error_code']}"
                self.info_error["text"] = self.error_msg

        if self.locked:
            self.client.run_async_program(stop_a)

    async def init_prog(self):
        await self.client.wait_for_status_set({self.client.NODE_STATUS_AVAILABLE,
                                               self.client.NODE_STATUS_BUSY,
                                               self.client.NODE_STATUS_READY})
        self.node = self.client.first_node()
        self.set_title()
        await self.node.watch(variables=True)

    def lock_node(self, locked):
        if locked:
            self.node.send_lock_node()
            self.robot_menu.entryconfig("Run", state="normal")
            self.robot_menu.entryconfig("Stop", state="normal")
        else:
            self.node.send_unlock_node()
            self.robot_menu.entryconfig("Run", state="disabled")
            self.robot_menu.entryconfig("Stop", state="disabled")
        self.locked = locked

    def remove_variable_view(self):
        if self.canvas is not None:
            self.canvas.destroy()
            self.canvas = None
            self.frame = None
            self.scrollbar.destroy()
            self.scrollbar = None

    def create_variable_row(self, name, value):
        f = tk.Frame(self.frame)
        f.pack(fill=tk.X, expand=True)
        title = name + (f"[{len(value)}]" if len(value) > 1 else "")
        l = tk.Label(f, text=title, anchor="w", width=25)
        l.pack(side=tk.LEFT)
        text = ", ".join([str(item) for item in value])
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

    def create_variable_view(self):
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
            for name in self.variables:
                self.create_variable_row(name, self.variables[name]["value"])

    def add_variable(self, name, value):
        if self.view_var.get() == 1 and value is not None:
            if name not in self.variables:
                self.create_variable_view()
                self.create_variable_row(name, value)
            else:
                text = ", ".join([str(item) for item in value])
                v = self.variables[name]
                v["text"] = text
                v["vwidget"]["text"] = text
        else:
            # just remember value
            self.variables[name] = {
                "value": value
            }

    def clear_variables(self):
        self.end_editing(cancel=True)
        for name in self.variables:
            self.variables[name]["widget"].destroy()
        self.variables = {}
        self.remove_variable_view()

    def begin_editing(self, name):
        if self.node.status != self.client.NODE_STATUS_READY or not self.end_editing(keep_editing_on_error=True):
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
                    self.node.send_set_variables({self.edited_variable: new_value})
                except Exception as e:
                    print(type(e), e)
                    if keep_editing_on_error:
                        return False
            v["ewidget"].destroy()
            v["ewidget"] = None
            self.edited_variable = None
        return True

    def remove_program_view(self):
        if self.text_program is not None:
            self.program_src = self.text_program.get("1.0", "end")
            self.text_program.destroy()
            self.text_program = None
            self.scrollbar.destroy()
            self.scrollbar = None

    def create_program_view(self):
        if self.frame is None:
            self.scrollbar = tk.Scrollbar(self.main_content, orient="vertical")
            self.scrollbar.pack(side=tk.RIGHT, fill="y")
            self.text_program = tk.Text(self.main_content, yscrollcommand=self.scrollbar.set)
            self.text_program.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.scrollbar.config(command=self.text_program.yview)
            if self.program_src.strip():
                self.text_program.insert("1.0", self.program_src)
            self.text_program.focus_set()

    def connect(self):

        def on_nodes_changed(nodes):
            self.node = (nodes[0]
                         if len(nodes) > 0 and nodes[0].status != self.client.NODE_STATUS_DISCONNECTED
                         else None)
            if self.node is None:
                self.clear_variables()
                self.set_title()
                self.info_mode["text"] = ""
            else:
                self.info_mode["text"] = {
                    self.client.NODE_STATUS_UNKNOWN: "No robot",
                    self.client.NODE_STATUS_CONNECTED: "Robot connected",
                    self.client.NODE_STATUS_AVAILABLE: "Observe",
                    self.client.NODE_STATUS_BUSY: "Observe (robot busy)",
                    self.client.NODE_STATUS_READY: "Control",
                    self.client.NODE_STATUS_DISCONNECTED: "Robot disconnected",
                }[self.node.status]
                # new node, set it up by starting coroutine
                self.start_co = self.init_prog()
                # disable menu Control if busy
                if self.node.status in {self.client.NODE_STATUS_AVAILABLE,
                                        self.client.NODE_STATUS_READY}:
                    self.robot_menu.entryconfig("Control", state="normal")
                else:
                    self.robot_menu.entryconfig("Control", state="disabled")

        def on_variables_changed(node, variables):
            if self.edited_variable is None:
                for name in variables:
                    if variables[name] is not None:
                        self.add_variable(name, variables[name])

        self.client = ClientAsync(tdm_addr=self.tdm_addr, tdm_port=self.tdm_port, debug=self.debug)
        self.client.on_nodes_changed = on_nodes_changed
        self.client.add_variables_changed_listener(on_variables_changed)
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


def help():
    print("""Usage: python3 -m tdmclient.tools.variables [options]
Variable browser and code editor

Options:
  --debug n    display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help       display this help message and exit
  --language=L programming language (aseba or python); default=automatic
  --tdmaddr=H  tdm address (default: localhost or from zeroconf)
  --tdmport=P  tdm port (default: from zeroconf)
""")


if __name__ == "__main__":

    debug = 0
    language = None  # auto
    tdm_addr = None
    tdm_port = None

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "help",
                                              "language=",
                                              "tdmaddr=",
                                              "tdmport=",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--debug":
            debug = int(val)
        elif arg == "--language":
            language = val
        elif arg == "--tdmaddr":
            tdm_addr = val
        elif arg == "--tdmport":
            tdm_port = int(val)

    win = VariableTableWindow(tdm_addr=tdm_addr, tdm_port=tdm_port, language=language, debug=debug)
    win.connect()
    win.mainloop()
