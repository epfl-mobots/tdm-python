# This file is part of tdmclient.
# Copyright 2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""Execute Aseba bytecode using package "dukpy" and vpl-web's vm in JavaScript.
"""

import dukpy
import json
import os

class AsebaVM:

    SRC_RUN = """
var asebaNode = new A3a.Node(A3a.thymioDescr);
var vthymio = new A3a.Device.VirtualThymio();
var events = [];
vthymio.onEmit = function (eventId, eventData) {
    events.push([eventId, eventData]);
};

function sendEvent(eventId) {
    vthymio.setupEvent(eventId);
    vthymio.run();
}

var r = null;
try {
    vthymio.setBytecode(bc);
    vthymio.reset();
    vthymio.flagStepByStep = false;
    vthymio.run();

    if (eventId != null) {
        sendEvent(eventId);
    }

    r = JSON.stringify({
        "data": vthymio.varData,
        "variables": vthymio.variables,
        "events": events
    });
} catch (e) {
    r = JSON.stringify({
        "error": e.toString()
    });
}
r
"""  # expect bc (array of int) and eventId (integer or null)

    def __init__(self, rel_path_vpl="../../../vpl-web/src/"):

        path_vpl = os.path.dirname(os.path.realpath(__file__)) + "/" + rel_path_vpl
        self.src_preamble = ""
        for filename in (
            "a3a-ns.js",
            "a3a-device.js",
            "a3a-virtual-thymio.js",
            "a3a-nodebase.js",
        ):
            with open(path_vpl + filename) as f:
                self.src_preamble += f.read()

        # patch for dukpy
        self.src_preamble = self.src_preamble.replace("Math.trunc", "Math.floor")

        self.aseba_bc = [0]
        self.data = []
        self.variables = {}
        self.events = []

    def set_bytecode(self, aseba_bytecode):
        self.aseba_bc = aseba_bytecode

    def build_js_src(self, event_id=None):
        src = ""
        src += f"bc = {json.dumps(self.aseba_bc)};\n"
        src += f"eventId = {json.dumps(event_id) if event_id is not None else 'null'};\n"
        src += self.src_preamble + self.SRC_RUN
        return src

    def run(self, event_id=None):
        src = self.build_js_src(event_id)
        r = json.loads(dukpy.evaljs(src))
        if "error" in r:
            raise Exception(r["error"])
        self.data = r["data"]
        self.variables = r["variables"]
        self.events = r["events"]

    def get_variables(self):
        return self.variables

    def get_data(self):
        return self.data

    def get_variable(self, name, variables):
        for variable_descr in variables:
            if variable_descr["name"] == name:
                return self.data[variable_descr["offset"] : variable_descr["offset"] + variable_descr["size"]]

    def get_events(self):
        return self.events
