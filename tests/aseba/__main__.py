from tdmclient.atranspiler import ATranspiler
from .compiler import AsebaCompiler
import sys
import getopt

def help(**kwargs):
    print(f"""Usage: python3 -m aseba [options]
Run compiler and vm.

Options:

  --aseba      Aseba source code input (default: Python)
  --bc         compile stdin and display bytecode
  --help       display this help message and exit
  --verbose    display more informations
""", **kwargs)

action = ""
is_aseba = False
verbose = False

try:
    arguments, values = getopt.getopt(sys.argv[1:],
                                      "",
                                      [
                                          "aseba",
                                          "bc",
                                          "help",
                                          "verbose",
                                      ])
except getopt.error as err:
    print(str(err))
    sys.exit(1)

for arg, val in arguments:
    if arg == "--aseba":
        is_aseba = True
    elif arg == "--bc":
        action = "bc"
    elif arg == "--help":
        help()
        sys.exit(0)
    elif arg == "--verbose":
        verbose = True

if action == "bc":
    c = AsebaCompiler()
    src = sys.stdin.read()
    if not is_aseba:
        src = ATranspiler.simple_transpile(src)
        if verbose:
            print("Transpiled source code:")
            print(src)
    c.compile(src)
    print(c.bc)
else:
    help()
