# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

class TDMZeroconfBrowser:

    def __init__(self, on_change=None, **kwargs):

        from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

        def on_service_state_change(zeroconf, service_type, name, state_change):
            if on_change and state_change in [ServiceStateChange.Added,
                                              ServiceStateChange.Removed]:
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    if info.properties and b"ws-port" in info.properties:
                        ws_port = int(info.properties[b"ws-port"])
                    else:
                        ws_port = None
                    for addr in info.parsed_addresses():
                        on_change(state_change is ServiceStateChange.Added,
                                  addr, info.port, ws_port)

        self.zeroconf = Zeroconf(**kwargs)
        self.browser = ServiceBrowser(self.zeroconf,
                                      ["_mobsya._tcp.local."],
                                      handlers=[on_service_state_change])

    def close(self):
        self.zeroconf.close()

    def __enter__(self):
        return self

    def __exit__(self, type, val, tb):
        self.close()
