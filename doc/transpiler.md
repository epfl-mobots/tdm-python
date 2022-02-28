
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
- Integer and boolean base types. Both are stored as signed 16-bit numbers, without error on overflow.
- Global variables. Variables are collected from the left-hand side part of plain assignments (assignment to variables without indexing). For arrays, there must exist at least one assignment of a list, directly or indirectly (i.e. `a=[1,2];b=a` is valid). Size conflicts are flagged as errors.
- Expressions with scalar arithmetic, comparisons (including chained comparisons), and boolean logic and conditional expressions with short-circuit evaluation. Numbers and booleans can be mixed freely. The following Python operators and functions are supported: infix operators `+`, `-`, `*`, `//` (integer division), `%` (converted to modulo instead of remainder, whose sign can differ with negative operands), `&`, `|`, `^`, `<<`, `>>`, `==`, `!=`, `>`, `>=`, `<`, `<=`, `and`, `or`; prefix operators `+`, `-`, `~`, `not`; and functions `abs` and `len`.
- Constants `False` and `True`.
- Assignments of scalars to scalar variables or array elements; or lists to whole array variables.
- Augmented assignments `+=`, `-=`, `*=`, `//=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`.
- Lists as the values of assignments to list variables, the argument of `len`, or the arguments of native functions which expect arrays. Lists can be list variables, values between square brackets (`[expr1, expr2, ...]`), or product of a number with values between square brackets (`2 * [expr1, expr2, ...]` or `[expr1, expr2, ...] * 3`).
- Programming constructs `if` `elif` `else`, `while` `else`, `for` `in range` `else`, `pass`, `return`. The `for` loop must use a `range` generator with 1, 2 or 3 arguments.
- Functions with scalar arguments, with or without return value (either a scalar value in all `return` statement; or no `return` statement or only without value, and call from the top level of expression statements, i.e. not at a place where a value is expected). Variable-length arguments `*args` and `**kwargs`, default values and multiple arguments with the same name are forbidden. Variables are local unless declared as global or not assigned to. Thymio predefined variables must also be declared explicitly as global when used in functions. In Python, dots are replaced by underscores; e.g. `leds_top` in Python corresponds to `leds.top` in Aseba.
- Function definitions for event handlers with the `@onevent` decorator. The function name must match the event name (such as `def timer0():` for the first timer event); except that dots are replaced by underscores in Python (e.g. `def button_left():`). Arguments are supported for custom events; they're initialized to `event.args[0]`, `event.args[1]`, etc. (the values passed to `emit`). Variables in event handlers behave like in plain function definitions.
- Option to check that local variables in plain functions or `@onevent` don't hide variables defined in the outer scope, which could result from forgetting to declare them global. This is implemented in `missing_global_decl` in `tdmclient.atranspiler_warnings` and enabled in command-line tools and Jupyter support with option `--warning-missing-global`.
- Function call `emit("name")` or `emit("name", param1, param2, ...)` to emit an event without or with parameters. The first argument must be a literal string, delimited with single or double quotes. Raw strings (prefixed with `r`) are allowed, f-strings or byte strings are not. Remaining arguments, if any, must be scalar expressions and are passed as event data.
- Function call `exit()` or `exit(code)`. An event `_exit` is emitted with the code value (0 by default). It's up to the program on the PC side to accept events, recognize those named `_exit`, stop the Thymio, and handle the code in a suitable way. The tool `tdmclient.tools.run` exits with the code value as its status.
- Function call `print` with arguments which can be any number of constant strings and scalar values. An event `_print` is emitted where the first value is the print statement index, following values are scalar values (int or boolean sent as signed 16-bit integer), with possibly additional 0 to have the same number of values for all the print statements. Format strings, built by concatenating the string arguments of `print` and `'%d'` to stand for numbers, can be retrieved separately. E.g. `print("left",motor_left_target)` could be transpiled to `emit _print [0, motor.left.target]` and the corresponding format string is `'left %d'`. It's up to the program on the PC side to accept events, recognize those named `_print`, extract the format string index and the arguments, and produce an output string with the `%` operator. The tool `tdmclient.tools.run` and the Jupyter notebook handle that.
- In expression statements, in addition to function calls, the ellipsis `...` can be used as a synonym of `pass`.

Perhaps the most noticeable yet basic missing features are the non-integer division operator `/` (Python has operator `//` for the integer division), and the `break` and `continue` statements, also missing in Aseba and difficult to transpile to sane code without `goto`. More generally, everything related to object-oriented programming, dynamic types, strings, and nested functions is not supported.

The transpilation is mostly straightforward. Mixing numeric and boolean expressions often requires splitting them into multiple statements and using temporary variables. The `for` loop is transpiled to an Aseba `while` loop because in Aseba, `for` is limited to constant ranges. Comments are lost because the official Python parser used for the first phase ignores them. Since functions are transpiled to subroutines, recursive functions are forbidden.

### Examples

#### Blinking

Blinking top RGB led:
```
on = False
timer_period[0] = 500

@onevent
def timer0():
    global on, leds_top
    on = not on
    if on:
        leds_top = [32, 32, 0]
    else:
        leds_top = [0, 0, 0]
```

To transpile this program, assuming it's stored in `examples/blink.py`:
```
python3 -m tdmclient.tools.transpile examples/blink.py
```

The result is
```
var on
var _timer0__tmp[1]

on = 0
timer.period[0] = 500

onevent timer0
    if on == 0 then
        _timer0__tmp[0] = 1
    else
        _timer0__tmp[0] = 0
    end
    on = _timer0__tmp[0]
    if on != 0 then
        leds.top = [32, 32, 0]
    else
        leds.top = [0, 0, 0]
    end
```

To run this program:
```
python3 -m tdmclient.tools.run examples/blink.py
```

#### Print

Constant strings and numeric values can be displayed on the computer with the `print` function. Here is an example which increments a counter every second and prints its value and whether it's odd or even:
```
i = 0

timer_period[0] = 1000

@onevent
def timer0():
    global i, leds_top
    i += 1
    is_odd = i % 2 == 1
    if is_odd:
        print(i, "odd")
        leds_top = [0, 32, 32]
    else:
        print(i, "even")
        leds_top = [0, 0, 0]
```

Running this program can also be done with `tdmclient.tools.run`. Assuming it's stored in `examples/print.py`:
```
python3 -m tdmclient.tools.run examples/print.py
```
`tdmclient.tools.run` continues running forever to receive and display the outcome of `print`. To interrupt it, type control-C.

To understand what happens behind the scenes, display the transpiled program:
```
python3 -m tdmclient.tools.transpile examples/print.py
```

The result is
```
var i
var _timer0_is_odd
var _timer0__tmp[1]

i = 0
timer.period[0] = 1000

onevent timer0
    i += 1
    if i % 2 == 1 then
        _timer0__tmp[0] = 1
    else
        _timer0__tmp[0] = 0
    end
    _timer0_is_odd = _timer0__tmp[0]
    if _timer0_is_odd != 0 then
        emit _print [0, i]
        leds.top = [0, 32, 32]
    else
        emit _print [1, i]
        leds.top = [0, 0, 0]
    end
```

Each `print` statement in Python is converted to `emit _print`. The event data contains the `print` statement index (numbers 0, 1, 2, ...) and the numeric values. The string values aren't sent, because the Aseba programming language doesn't support strings. It's the responsibility of the receiver of the event, i.e. `tdmclient.tools.run` on the computer, to use the `print` statement index and assemble the text to be displayed from the constant strings and the numeric values received from the robot.

With the option `--print`, `tdmclient.tools.transpile` shows the Python dictionary which contains the format string for each `print` statement and the number of numeric arguments:
```
python3 -m tdmclient.tools.transpile --print examples/print.py
```

The result is
```
{0: ('%d odd', 1), 1: ('%d even', 1)}
```

### Feature comparison

The table below shows a mapping between Aseba and Python features. Empty cells stand for lack of a direct equivalent. Prefixes `const_`, `numeric_` or `bool_` indicate restrictions on what's permitted. Standard Python features which are missing are not transpiled; they cause an error.

| Aseba | Python
| --- | ---
| infix `+` `-` `*` `/` | infix `+` `-` `*` `//`
| infix `%` (remainder) | infix `%` (modulo)
| infix `<<` `>>` <code>&#124;</code> `&` `^` | infix `<<` `>>` <code>&#124;</code> `&` `^`
| prefix `-` `~` `not` | prefix `-` `~` `not`
| | prefix `+`
| `==` `!=` `<` `<=` `>` `>=` | `==` `!=` `<` `<=` `>` `>=`
| | `a < b < c` (chained comparisons)
| `and` `or` (without shortcut) | `and` `or` (with shortcut)
| | `val1 if test else val2`
| prefix `abs` | function `abs(expr)`
| | `len(variable)`
| `var v` | no declarations
| `var a[size]` |
| `var a[] = [...]` | `a = [...]`
| | `a = number * [...]` `a = [...] * number`
| `v = numeric_expr` | `v = any_expr`
| `+=` `-=` `*=` `/=` `%=` `<<=` `>>=` `&=` <code>&#124;=</code> | `+=` `-=` `*=` `//=` `%=` `<<=` `>>=` `&=` <code>&#124;=</code>
| `v++` `v--` | `v += 1` `v -= 1`
| `a = b` (array assignment) | `a = b`
| `a[index_expr]` | `a[index_expr]`
| `a[constant_range]` |
| `if bool_expr then` | `if any_expr:`
| `elseif bool_expr then` | `elif any_expr:`
| `else` | `else:`
| `end` | indenting
| `when bool_expr do` |
| `while bool_expr do` | `while any_expr:`
| `for v in 0 : const_b - 1 do` | `for v in range(expr_b):`
| `for v in const_a : const_b - 1 do` | `for v in range(expr_a, expr_b):`
| `for v in const_a : const_b -/+ 1 step const_s do` | `for v in range(expr_a, expr_b, expr_s):`
| `sub fun` | `def fun():`
| all variables are global | `global g`
| | assigned variables are local by default
| | `def fun(arg1, arg2, ...):`
| `return` | `return`
| | `return expr`
| `callsub fun` | `fun()`
| | `fun(expr1, expr2, ...)`
| | `fun(...)` in expression
| `onevent name` | `@onevent` `def name():`
| `onevent name` `arg1=event.args[0] ...` | `@onevent` `def name(arg1, ...):`
| all variables are global | `global g`
| | assigned variables are local by default
| `emit name` | `emit("name")`
| `emit name [expr1, expr2, ...]` | `emit("name", expr1, expr2, ...)`
| explicit event declaration outside program | no event declaration
| | `print(...)`
| `call natfun(expr1, expr2, ...)` | `nf_natfun(expr1, expr2, ...)` (see below)
| | `natfun(expr1, ...)` in expressions

In Python, the names of native functions have underscores instead of dots. Many native functions can be called with the syntax of a plain function call, with a name prefixed with `nf_` and the same arguments as in Aseba. In the table below, uppercase letters stand for arrays (lists in Python), lowercase letters for scalar values, `A`, `B`, `a` and `b` for inputs, `R` and `r` for result, and `P` for both input and result. Lists can be variables or lists of numbers and/or booleans.

Arguments are the same in the same order, except for `_system.settings.read` which returns a single scalar value. In Python, scalar numbers are passed by value and not by reference, contrary to Aseba; therefore the result is passed as a return value and can be used directly in any expression. Note also that in Python, lists (arrays) of length 1 are _not_ interchangeable with scalars, contrary to Aseba.

| Aseba | Python
| --- | ---
| `call math.copy(R, A)` | `nf_math_copy(R, A)`
| `call math.fill(R, a)` | `nf_math_fill(R, a)`
| `call math.addscalar(R, A, b)` | `nf_math_addscalar(R, A, b)`
| `call math.add(R, A, B)` | `nf_math_add(R, A, B)`
| `call math.sub(R, A, B)` | `nf_math_sub(R, A, B)`
| `call math.mul(R, A, B)` | `nf_math_mul(R, A, B)`
| `call math.div(R, A, B)` | `nf_math_div(R, A, B)`
| `call math.min(R, A, B)` | `nf_math_min(R, A, B)`
| `call math.max(R, A, B)` | `nf_math_max(R, A, B)`
| `call math.clamp(R, A, B, C)` | `nf_math_clamp(R, A, B, C)`
| `call math.rand(R)` | `nf_math_rand(R)`
| `call math.sort(P)` | `nf_math_sort(P)`
| `call math.muldiv(R, A, B, C)` | `nf_math_muldiv(R, A, B, C)`
| `call math.atan2(R, A, B)` | `nf_math_atan2(R, A, B)`
| `call math.sin(R, A)` | `nf_math_sin(R, A)`
| `call math.cos(R, A)` | `nf_math_cos(R, A)`
| `call math.rot2(R, A, b)` | `nf_math_rot2(R, A, b)`
| `call math.sqrt(R, A)` | `nf_math_sqrt(R, A)`
| `call _leds.set(a, b)` | `nf__leds_set(a, b)`
| `call _poweroff()` | `nf__poweroff()`
| `call _system.reboot()` | `nf__system_reboot()`
| `call _system.settings.read(a, r)` | `r = nf__system_settings_read(a)`
| `call _system.settings.write(a, b)` | `nf__system_settings_write(a, b)`
| `call _leds.set(i, br)` | `nf__leds_set(i, br)`
| `call sound.record(i)` | `nf_sound_record(i)`
| `call sound.play(i)` | `nf_sound_play(i)`
| `call sound.replay(i)` | `nf_sound_replay(i)`
| `call sound.duration(i, d)` | `d = nf_sound_duration(i)`
| `call sound.system(i)` | `nf_sound_system(i)`
| `call leds.circle(br0,br1,br2,br3,br4,br5,br6,br7)` | `nf_leds_circle(br0,br1,br2,br3,br4,br5,br6,br7)`
| `call leds.top(r, g, b)` | `nf_leds_top(r, g, b)`
| `call leds.bottom.right(r, g, b)` | `nf_leds_bottom.right(r, g, b)`
| `call leds.bottom.left(r, g, b)` | `nf_leds_bottom_left(r, g, b)`
| `call leds.buttons(br0,br1,br2,br3)` | `nf_leds_buttons(br0,br1,br2,br3)`
| `call leds.leds.prox.h(br0,br1,br2,br3,br4,br5,br6,br7)` | `nf_leds_prox_h(br0,br1,br2,br3,br4,br5,br6,br7)`
| `call leds.leds.prox.v(br0, br1)` | `nf_leds_prox_v(br0, br1)`
| `call leds.rc(br)` | `nf_leds_rc(br)`
| `call leds.sound(br)` | `nf_leds_sound(br)`
| `call leds.temperature(r, g)` | `nf_leds_temperature(r, g)`
| `call sound.freq(f, d)` | `nf_sound_freq(f, d)`
| `call sound.wave(W)` | `nf_sound_wave(W)`
| `call prox.comm.enable(en)` | `nf_prox_comm_enable(en)`
| `call sd.open(i, status)` | `status = nf_sd_open(i)`
| `call sd.write(data, n)` | `n = nf_sd_write(data)`
| `call sd.read(data, n)` | `n = nf_sd_read(data)`
| `call sd.seek(pos, status)` | `status = nf_sd_seek(pos)`
| `call deque.size(queue, n)` | `n = nf_deque_size(queue)`
| `call deque.push_front(queue, data)` | `nf_deque_push_front(queue, data)`
| `call deque.push_back(queue, data)` | `nf_deque_push_back(queue, data)`
| `call deque.pop_front(queue, data)` | `nf_deque_pop_front(queue, data)`
| `call deque.pop_back(queue, data)` | `nf_deque_pop_back(queue, data)`
| `call deque.get(queue, data, i)` | `nf_deque_get(queue, data, i)`
| `call deque.set(queue, data, i)` | `nf_deque_set(queue, data, i)`
| `call deque.insert(queue, data, i)` | `nf_deque_insert(queue, data, i)`
| `call deque.erase(queue, i, len)` | `nf_deque_erase(queue, i, len)`


Some math functions have an alternative name without the `nf_` prefix, scalar arguments and a single scalar result. They can be used in assignments or other expressions.

| Aseba native function | Python function call
| --- | ---
| `math.min` | `math_min(a, b)`
| `math.max` | `math_max(a, b)`
| `math.clamp` | `math_clamp(a, b, c)`
| `math.rand` | `math_rand()`
| `math.muldiv` | `math_muldiv(a, b, c)`
| `math.atan2` | `math_atan2(a, b)`
| `math.sin` | `math_sin(a)`
| `math.cos` | `math_cos(a)`
| `math.sqrt` | `math_sqrt(a)`

## Thymio variables and native functions

Thymio variables and native functions are mapped to Thymio's. Their names contain underscores `_` instead of dots '.'; e.g. `leds_top` in Python instead of `leds.top` in Aseba. By default, they're predefined in the global scope. Alternatively, with option `--nothymio` in  `tdmclient.tools.transpile` or `tdmclient.tools.run`, they aren't, but can be imported from module `thymio` as follows:
- `import thymio` in the global scope: variables can be accessed everywhere in expressions or assignments as e.g. `thymio.leds_top`.
- `import thymio as A` in global scope: variables can be accessed everywhere in expressions or assignments as e.g. `A.leds_top` (`A` can be any valid symbol).
- `import thymio` or `import thymio as A` in function definition scope: variables can be accessed in expressions or assignments in the function.
- `from thymio import s1, s2, ...` in the global scope: variables can be accessed in expressions everywhere (except in functions where a local variables with the same name is assigned to), in assignments in the global scope, and in functions where `s1`, `s2` etc. are declared global.
- `from thymio import *` in the global scope: all Thymio symbols are imported and can be accessed directly by their name.
- `from thymio import s1 as a1, s2 as a2, ...` in the global scope: same as above, but variables (or only some of them) are aliased to a different name.
- `from thymio import ...` in function definition scope: variables can be accessed in expressions or assignments in the function.

In other words, the expected Python rules apply.

In addition to variables and native functions, the following constants are defined:

| Name | Value
| --- | ---
| `BLACK` | `[0, 0, 0]`
| `BLUE` | `[0, 0, 32]`
| `CYAN` | `[0, 32, 32]`
| `GREEN` | `[0, 32, 0]`
| `MAGENTA` | `[32, 0, 32]`
| `RED` | `[32, 0, 0]`
| `WHITE` | `[32, 32, 32]`
| `YELLOW` | `[32, 32, 0]`

Function `emit` and decorator `@onevent` are always predefined. This is also the case for `abs`, `exit`, `len` and `print`, like in plain Python.

Here are examples which all transpile to the same Aseba program `leds.top = [32, 0, 0]`:
```
import thymio
thymio.leds_top = thymio.RED
```
```
from thymio import leds_top, RED
leds_top = RED
```
```
from thymio import leds_top
from thymio import RED
leds_top = RED
```
```
import thymio
from thymio import leds_top
leds_top = thymio.RED
```
```
from thymio import *
leds_top = RED
```
```
from thymio import leds_top as led, RED as color
led = color
```

## Module `clock`

In addition to `thymio`, there is one other module available. The module `clock` provides functions to get the current time since the start of the program or the last call to its function `reset()`. It can be used to measure the time between two events or to add time information to data sent from the robot to the PC with events.

The module implements the following functions:

| Function | Description
| --- | ---
| `reset()` | reset the tick counter (restart times from 0)
| `seconds()` | time in second
| `ticks_50Hz()` | time in 1/50 second

The values are based on a counter incremented 50 times per second. Since it's stored in a signed 16-bit integer, like all Thymio variables, there is an overflow after 32767/50 seconds, or 5 minutes and 55 seconds. If your program runs longer, use the clock to measure smaller intervals and reset it for each new interval.
