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
- Programming constructs `if` `elif` `else`, `while` `else`, `for` `in range` `else`, `pass`, `return`. The `for` loop must use a `range` generator with 1, 2 or 3 arguments.
- Functions with scalar arguments, with or without return value (either a scalar value in all `return` statement; or no `return` statement or only without value, and call from the top level of expression statements, i.e. not at a place where a value is expected). Variable-length arguments `*args` and `**kwargs`, default values and multiple arguments with the same name are forbidden. Variables are local unless declared as global or not assigned to. Thymio predefined variables must also be declared explicitly as global when used in functions. In Python, dots are replaced by underscores; e.g. `leds_top` in Python corresponds to `leds.top` in Aseba.
- Function definitions for event handlers with the `@onevent` decorator. The function name must match the event name (such as `def timer0():` for the first timer event). Arguments are not supported; otherwise variables in event handlers behave like in plain function definitions.
- Function call `emit("name")` or `emit("name", param1, param2, ...)` to emit an event without or with parameters. The first argument must be a literal string, delimited with single or double quotes. Raw strings (prefixed with `r`) are allowed, f-strings or byte strings are not. Remaining arguments, if any, must be scalar expressions and are passed as event data.
- In expression statements, in addition to function calls, the ellipsis `...` can be used as a synonym of `pass`.

Perhaps the most noticeable missing features are the non-integer division operator `/` (Python has operator `//` for the integer division), and the `break` and `continue` statements, also missing in Aseba and difficult to transpile to sane code without `goto`. High on our to-do list: functions with arguments and return value.

The transpilation is mostly straightforward. Mixing numeric and boolean expressions often requires splitting them into multiple statements and using temporary variables. The `for` loop is transpiled to an Aseba `while` loop because in Aseba, `for` is limited to constant ranges. Comments are lost because the official Python parser used for the first phase ignores them. Since functions are transpiled to subroutines, recursive functions are forbidden.

### Example

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
python3 -m tdmclient.atranspiler examples/blink.py
```

The result is
```
var on
var tmp[1]

on = 0
timer.period[0] = 500

onevent timer0
    if on == 0 then
        tmp[0] = 1
    else
        tmp[0] = 0
    end
    on = tmp[0]
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

### Feature comparison

The table below shows a mapping between Aseba and Python features. Empty cells stand for lack of a direct equivalent. Prefixes `const_`, `numeric_` or `bool_` indicate restrictions on what's permitted. Standard Python features which are missing are not transpiled; they cause an error.

| Aseba | Python
| --- | ---
| infix `+` `-` `*` `/` | infix `+` `-` `*` `//` `%`
| infix `%` (remainder) | infix `%` (modulo)
| infix `<<` `>>` `|` `&` `^` | infix `<<` `>>` `|` `&` `^`
| prefix `-` `~` `not` | prefix `-` `~` `not`
| | prefix +
| `==` `!=` `<` `<=` `>` `>=` | `==` `!=` `<` `<=` `>` `>=`
| | `a < b < c` (chained comparisons)
| `and` `or` (without shortcut) | `and` `or` (with shortcut)
| | `val1 if test else val2`
| `var v` | no declarations
| `var a[size]` |
| `var a[] = [...]` | `a = [...]`
| `v = numeric_expr` | `v = any_expr`
| `v[index_expr]` | `v[index_expr]`
| `v[constant_range]` |
| `if bool_expr then` | `if any_expr:`
| `elseif bool_expr then` | `elif any_expr:`
| `else` | `else:`
| `end` | indenting
| `when bool_expr do` |
| `while bool_expr do` | `while any_expr:`
| `for v in 0 : const_b - 1 do` | `for v in range(expr_a, expr_b):`
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
| all variables are global | `global g`
| | assigned variables are local by default
| `emit name` | `emit("name")`
| `emit name [expr1, expr2, ...]` | `emit("name", expr1, expr2, ...)`
| `call natfun expr1, expr2, ...` | `nf_natfun(expr1, expr2, ...)` (see below)
| | `natfun(expr1, ...)` in expressions

In Python, the names of native functions have underscores instead of dots. Many native functions can be called with the syntax of a plain function call, with a name prefixed with `nf_` and the same arguments as in Aseba. In the table below, uppercase letters stand for arrays, lowercase letters for scalar values, `A`, `B`, `a` and `b` for inputs, `R` and `r` for result, and `P` for both input and result.

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

A few of them have a name without the `nf_` prefix, scalar arguments and a single scalar result. They can be used in an assignment or in expressions.

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
