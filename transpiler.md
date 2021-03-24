## Python-to-Aseba transpiler

The official programming language of the Thymio is Aseba, a rudimentary event-driven text language. In the current official software environment, it's compiled by the TDM to machine code for a virtual processor, which is itself a program which runs on the Thymio. Virtual processors are common on many platforms; they're often referred as _VM_ (Virtual Machine), and their machine code as _bytecode_.

Most programming languages for the Thymio eventually involve bytecode running on its VM. They can be divided into two main categories:
- Programs compiled to bytecode running autonomously in the VM on the microcontroller of the Thymio. In Thymio Suite and its predecessor Aseba Studio, this includes the Aseba language; and VPL, VPL&nbsp;3, and Blockly, where programs are made of graphical representations of programming constructs and converted to bytecode in two steps, first to Aseba, then from Aseba to bytecode with the standard TDM Aseba compiler.
- Programs running on the computer and controlling the Thymio remotely. In Thymio Suite and Aseba Studio, this includes Scratch. Python programs which use `thymiodirect` or `tdmclient` can also belong to this category. A small Aseba program runs on the Thymio, receives commands and sends back data via events.

Exceptions would include programs which control remotely the Thymio exclusively by fetching and changing variables; and changing the Thymio firmware, the low-level program compiled directly for its microcontroller.

Remote programs can rely on much greater computing power and virtually unlimited data storage capacity. On the other hand, communication is slow, especially with the USB radio dongle. It restricts what can be achieved in feedback loops when commands to actuators are based on sensor measurements.

Alternative compilers belonging to the first category, not needing the approval of Mobsya, are possible and have actually been implemented. While the Thymio VM is tightly coupled to the requirements of the Aseba language, some of the most glaring Aseba language limitations can be circumvented. Ultimately, the principal restrictions are the amount of code and data memory and the execution speed.

Sending arbitrary bytecode to the Thymio cannot be done by the TDM. The TDM accepts only Aseba source code, compiles it itself, and sends the resulting bytecode to the Thymio. So with the TDM, to support alternative languages, we must convert them to Aseba programs. To send bytecode, or assembly code which is a bytecode text representation easier to understand for humans, an alternative would be the Python package `thymiodirect`.

Converting source code (the original text program representation) from a language to another one is known as _transpilation_ (or _transcompilation_). This document describes a transpiler which converts programs from Python to Aseba. Its goal is to run Python programs locally on the Thymio, be it for autonomous programs or for control and data acquisition in cooperation with the computer via events. Only a small subset of Python is supported. Most limitations of Aseba are still present.

### Features

The transpiler is implemented in class `ATranspiler`, completely independently of other `tdmclient` functionality. The input is a complete program in Python; the output is an Aseba program.

Here are the implemented features:
- Python syntax. The official Python parser is used, hence no surprise should be expected, including with spaces, tabs, parentheses, and comments.
- Global variables. Variables are collected from the left-hand side part of plain assignments (assignment to variables without indexing). For arrays, there must exist at least one assignment of a list, directly or indirectly (i.e. `a=[1,2];b=a` is valid). Size conflicts are flagged as errors.
- Expressions with scalar arithmetic, comparisons and boolean logic with short-circuit evaluation. Numbers and booleans can be mixed freely. The following Python operators are supported: infix operators `+`, `-`, `*`, `//` (integer division), `%` (converted to modulo instead of remainder, whose sign can differ with negative operands), `&`, `|`, `^`, `<<`, `>>`, `==`, `!=`, `>`, `>=`, `<`, `<=`; and prefix operators `+`, `-`, `~`, `not`.
- Constants `False` and `True`.
- Assignments of scalars to scalar variables or array elements; or lists to whole array variables.
- Programming constructs `if` `elseif` `else`, `while` `else`, `for` `in range` `else`, `pass`, `return`. The `for` loop must use a `range` generator with 1, 2 or 3 arguments.
- Functions exclusively for event handlers with the `@onevent` decorator. The function name must match the event name (such as `def timer0():` for the first timer event). Arguments are not supported.

Currently, a major difference with the semantic of Python is that all variables are global. This is not satisfactory and is likely to be fixed soon. To ensure forward compatibility, variables in functions (currently for event handlers) should be declared in a `global` statement, which is ignored currently; or be local and avoid any conflict elsewhere in the code (i.e. reusing a variable `i` in two loops is fine provided that the loops are not nested).

The transpilation is mostly straightforward. Mixing numeric and boolean expressions often requires splitting them into multiple statements and using temporary variables. The `for` loop is transpiled to an Aseba `while` loop because in Aseba, `for` is limited to constant ranges.

### Example

Blinking top RGB led:
```
on = False
timer.period[0] = 500

@onevent
def timer0():
    global on
    on = not on
    if on:
        leds.top = [32, 32, 0]
    else:
        leds.top = [0, 0, 0]
```

To transpile this program, assuming it's stored in `examples/blink.py`:
```
python3 -m tdmclient.atranspiler examples/blink.py
```
