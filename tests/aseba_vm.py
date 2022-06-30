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

class AsebaVM:

    SRC_RUN = """
var asebaNode = new A3a.Node(A3a.thymioDescr);
var vthymio = new A3a.Device.VirtualThymio();
/*
vthymio.onVarChanged = function (name, index, newValue, oldValue, oldArrayValue) {
    print(name, index, newValue, oldValue, oldArrayValue);
    print("vthymio.varData", vthymio.varData);
};
*/

function sendEvent(name) {
    var eventId = asebaNode.eventNameToId(name);
    vthymio.setupEvent(eventId);
    vthymio.run();
}

vthymio.setBytecode(bc);
vthymio.reset();
vthymio.flagStepByStep = false;
vthymio.run();

if (eventName) {
    sendEvent(eventName);
}

JSON.stringify({
    "data": vthymio.varData,
    "variables": vthymio.variables
});
"""  # expect bc (array of int) and eventName (string or null)

    def __init__(self, path_vpl="../../vpl-web/src/"):

        self.src_preamble = ""
        for filename in (
            "a3a-ns.js",
            "a3a-device.js",
            "a3a-virtual-thymio.js",
            "a3a-nodebase.js",
        ):
            with open(path_vpl + filename) as f:
                self.src_preamble += f.read()

        self.aseba_bc = [0]

    def set_bytecode(self, aseba_bytecode):
        self.aseba_bc = aseba_bytecode

    def build_js_src(self, event_name=None):
        src = ""
        src += f"bc = {json.dumps(self.aseba_bc)};\n"
        src += f"eventName = {json.dumps(event_name) if event_name is not None else 'null'};\n"
        src += self.src_preamble + self.SRC_RUN
        return src

    def run(self, event_name=None):
        src = self.build_js_src(event_name)
        r = json.loads(dukpy.evaljs(src))
        self.data = r["data"]
        self.variables = r["variables"]

    def get_variables(self):
        return self.variables

    def get_data(self):
        return self.data

    def get_variable(self, name, variables):
        for variable_descr in variables:
            if variable_descr["name"] == name:
                return self.data[variable_descr["offset"] : variable_descr["offset"] + variable_descr["size"]]
