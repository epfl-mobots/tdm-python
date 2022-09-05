import unittest
from tdmclient.atranspiler import ATranspiler
from aseba import AsebaCompiler, AsebaVM

class TestTranspiler(unittest.TestCase):

    def test_empty(self):
        src_py = ""
        src_a = ATranspiler.simple_transpile(src_py).strip()
        self.assertEqual(src_a, "")

    def test_comment(self):
        src_py = "# comment"
        src_a = ATranspiler.simple_transpile(src_py).strip()
        self.assertEqual(src_a, "")

    def test_decl_scalar_var(self):
        src_py = "a = 123"
        src_a = ATranspiler.simple_transpile(src_py).strip()
        self.assertTrue(src_a.startswith("var a"))
        self.assertFalse("a[" in src_a)

    def test_assign_scalar_var(self):
        src_py = "a = 123"
        src_a = ATranspiler.simple_transpile(src_py).replace(" ", "")
        self.assertTrue("a=123" in src_a)

    def test_assign_list(self):
        src_py = "a = [1,2,3]"
        src_a = ATranspiler.simple_transpile(src_py).replace(" ", "")
        self.assertTrue("a=[1,2,3]" in src_a)

    # tests below: based on aseba_compiler.py and aseba_vm.py,
    # which require dukpy and a clone of vpl-web in a sibbling directory

    def assert_transpiled_code_result(self, src_py, assertTrueFun, emit=None):
        """Transpile Python code, compile it, execute it on a vm, send the
        event whose name is specified by argument emit (unless None) and
        execute assertTrueFun(var_getter)
        """
        src_a = ATranspiler.simple_transpile(src_py)
        c = AsebaCompiler()
        c.compile(src_a)
        v = AsebaVM()
        v.set_bytecode(c.bc)
        event_id = c.event_name_to_event_id(emit) if emit is not None else None
        v.run(event_id=event_id)

        def getter(name):
            """Get the array value of a variable specified by its name, or (if
            name is None) an array of events, each event as [id, data]
            """
            if name is not None:
                return v.get_variable(name, c.variable_descriptions)
            else:
                return v.get_events()

        b = assertTrueFun(getter)
        if not b:
            print(f"""
src_py:
{src_py}
src_aseba:
{src_a}
""")
        self.assertTrue(b)

    # simple assignments

    def test_assign_scalar_result(self):
        self.assert_transpiled_code_result(
            "a = 123",
            lambda getter: getter("a") == [123]
        )

    def test_assign_list_result(self):
        self.assert_transpiled_code_result(
            "a = [1, 2, 3]",
            lambda getter: getter("a") == [1, 2, 3]
        )

    # operators with constant operands

    def test_const_plus(self):
        self.assert_transpiled_code_result(
            "a = 1 + 2",
            lambda getter: getter("a") == [3]
        )

    def test_const_minus(self):
        self.assert_transpiled_code_result(
            "a = 1 - 2",
            lambda getter: getter("a") == [-1]
        )

    def test_const_times(self):
        self.assert_transpiled_code_result(
            "a = 2 * 3",
            lambda getter: getter("a") == [6]
        )

    def test_const_divide(self):
        self.assert_transpiled_code_result(
            "a = 7 // 2",
            lambda getter: getter("a") == [3]
        )

    def test_const_modulo(self):
        self.assert_transpiled_code_result(
            "a = 7 % 5",
            lambda getter: getter("a") == [2]
        )

    def test_const_bitwise_and(self):
        self.assert_transpiled_code_result(
            "a = 0b1100 & 0b1010",
            lambda getter: getter("a") == [0b1100 & 0b1010]
        )

    def test_const_bitwise_or(self):
        self.assert_transpiled_code_result(
            "a = 0b1100 | 0b1010",
            lambda getter: getter("a") == [0b1100 | 0b1010]
        )

    def test_const_bitwise_xor(self):
        self.assert_transpiled_code_result(
            "a = 0b1100 ^ 0b1010",
            lambda getter: getter("a") == [0b1100 ^ 0b1010]
        )

    def test_const_sl(self):
        self.assert_transpiled_code_result(
            "a = 7 << 2",
            lambda getter: getter("a") == [7 << 2]
        )

    def test_const_sr(self):
        self.assert_transpiled_code_result(
            "a = 127 >> 3",
            lambda getter: getter("a") == [127 >> 3]
        )

    def test_const_eq(self):
        self.assert_transpiled_code_result(
            "a = [2 == 1, 2 == 2, 2 == 3]",
            lambda getter: getter("a") == [0, 1, 0]
        )

    def test_const_ne(self):
        self.assert_transpiled_code_result(
            "a = [2 != 1, 2 != 2, 2 != 3]",
            lambda getter: getter("a") == [1, 0, 1]
        )

    def test_const_gt(self):
        self.assert_transpiled_code_result(
            "a = [2 > 1, 2 > 2, 2 > 3]",
            lambda getter: getter("a") == [1, 0, 0]
        )

    def test_const_ge(self):
        self.assert_transpiled_code_result(
            "a = [2 >= 1, 2 >= 2, 2 >= 3]",
            lambda getter: getter("a") == [1, 1, 0]
        )

    def test_const_lt(self):
        self.assert_transpiled_code_result(
            "a = [2 < 1, 2 < 2, 2 < 3]",
            lambda getter: getter("a") == [0, 0, 1]
        )

    def test_const_le(self):
        self.assert_transpiled_code_result(
            "a = [2 <= 1, 2 <= 2, 2 <= 3]",
            lambda getter: getter("a") == [0, 1, 1]
        )

    def test_const_and(self):
        self.assert_transpiled_code_result(
            "a = [0 and 0, 0 and 1, 1 and 0, 1 and 1]",
            lambda getter: getter("a") == [0, 0, 0, 1]
        )

    def test_const_or(self):
        self.assert_transpiled_code_result(
            "a = [0 or 0, 0 or 1, 1 or 0, 1 or 1]",
            lambda getter: getter("a") == [0, 1, 1, 1]
        )

    def test_const_uplus(self):
        self.assert_transpiled_code_result(
            "a = +5",
            lambda getter: getter("a") == [5]
        )

    def test_const_uminus(self):
        self.assert_transpiled_code_result(
            "a = -(5)",
            lambda getter: getter("a") == [-5]
        )

    def test_const_cpl(self):
        self.assert_transpiled_code_result(
            "a = ~123",
            lambda getter: getter("a") == [-1 - 123]
        )

    def test_const_not(self):
        self.assert_transpiled_code_result(
            "a = [not False, not True]",
            lambda getter: getter("a") == [1, 0]
        )

    def test_const_abs(self):
        self.assert_transpiled_code_result(
            "a = [abs(-123), abs(456)]",
            lambda getter: getter("a") == [123, 456]
        )

    def test_const_len(self):
        self.assert_transpiled_code_result(
            "a = len([1,2,3,1,2,3])",
            lambda getter: getter("a") == [6]
        )

    # operators with variable operands

    def test_var_plus(self):
        self.assert_transpiled_code_result(
            "x = 1; y = 2; a = x + y",
            lambda getter: getter("a") == [3]
        )

    def test_var_minus(self):
        self.assert_transpiled_code_result(
            "x = 1; y = 2; a = x - y",
            lambda getter: getter("a") == [-1]
        )

    def test_var_times(self):
        self.assert_transpiled_code_result(
            "x = 2; y = 3; a = x * y",
            lambda getter: getter("a") == [6]
        )

    def test_var_divide(self):
        self.assert_transpiled_code_result(
            "x = 7; y = 2; a = x // y",
            lambda getter: getter("a") == [3]
        )

    def test_var_floatdivide(self):
        self.assertRaises(Exception,
                          ATranspiler.simple_transpile, "a = 2; b = 1 / a")

    def test_var_modulo(self):
        self.assert_transpiled_code_result(
            "x = 7; y = 5; a = x % y",
            lambda getter: getter("a") == [2]
        )

    def test_var_bitwise_and(self):
        self.assert_transpiled_code_result(
            "x = 0b1100; y = 0b1010; a = x & y",
            lambda getter: getter("a") == [0b1100 & 0b1010]
        )

    def test_var_bitwise_or(self):
        self.assert_transpiled_code_result(
            "x = 0b1100; y = 0b1010; a = x | y",
            lambda getter: getter("a") == [0b1100 | 0b1010]
        )

    def test_var_bitwise_xor(self):
        self.assert_transpiled_code_result(
            "x = 0b1100; y = 0b1010; a = x ^ y",
            lambda getter: getter("a") == [0b1100 ^ 0b1010]
        )

    def test_var_sl(self):
        self.assert_transpiled_code_result(
            "x = 7; y = 2; a = x << y",
            lambda getter: getter("a") == [7 << 2]
        )

    def test_var_sr(self):
        self.assert_transpiled_code_result(
            "x = 127; y = 3; a = x >> y",
            lambda getter: getter("a") == [127 >> 3]
        )

    def test_var_eq(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x == p, x == q, x == r]",
            lambda getter: getter("a") == [0, 1, 0]
        )

    def test_var_ne(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x != p, x != q, x != r]",
            lambda getter: getter("a") == [1, 0, 1]
        )

    def test_var_gt(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x > p, x > q, x > r]",
            lambda getter: getter("a") == [1, 0, 0]
        )

    def test_var_ge(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x >= p, x >= q, x >= r]",
            lambda getter: getter("a") == [1, 1, 0]
        )

    def test_var_lt(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x < p, x < q, x < r]",
            lambda getter: getter("a") == [0, 0, 1]
        )

    def test_var_le(self):
        self.assert_transpiled_code_result(
            "x = 2; p = 1; q = 2; r = 3; a = [x <= p, x <= q, x <= r]",
            lambda getter: getter("a") == [0, 1, 1]
        )

    def test_var_and(self):
        self.assert_transpiled_code_result(
            "zero = 0; one = 1; a = [zero and zero, zero and one, one and zero, one and one]",
            lambda getter: getter("a") == [0, 0, 0, 1]
        )

    def test_var_or(self):
        self.assert_transpiled_code_result(
            "zero = 0; one = 1; a = [zero or zero, zero or one, one or zero, one or one]",
            lambda getter: getter("a") == [0, 1, 1, 1]
        )

    def test_var_uplus(self):
        self.assert_transpiled_code_result(
            "x = 5; a = +x",
            lambda getter: getter("a") == [5]
        )

    def test_var_uminus(self):
        self.assert_transpiled_code_result(
            "x = 5; a = -x",
            lambda getter: getter("a") == [-5]
        )

    def test_var_cpl(self):
        self.assert_transpiled_code_result(
            "x = 123; a = ~x",
            lambda getter: getter("a") == [-1 - 123]
        )

    def test_var_not(self):
        self.assert_transpiled_code_result(
            "x = False; y = True; a = [not x, not y]",
            lambda getter: getter("a") == [1, 0]
        )

    def test_var_abs(self):
        self.assert_transpiled_code_result(
            "x = -123; y = 456; a = [abs(x), abs(y)]",
            lambda getter: getter("a") == [123, 456]
        )

    def test_var_len(self):
        self.assert_transpiled_code_result(
            "lst = [1,2,3,1,2,3]; a = len(lst)",
            lambda getter: getter("a") == [6]
        )

    # constants

    def test_var_cst(self):
        self.assert_transpiled_code_result(
            "a = [False, True]",
            lambda getter: getter("a") == [0, 1]
        )

    # augmented assignments

    def test_augmented_asgn_plus(self):
        self.assert_transpiled_code_result(
            "a = 5; a += 3",
            lambda getter: getter("a") == [8]
        )

    def test_augmented_asgn_minus(self):
        self.assert_transpiled_code_result(
            "a = 5; a -= 3",
            lambda getter: getter("a") == [2]
        )

    def test_augmented_asgn_times(self):
        self.assert_transpiled_code_result(
            "a = 5; a *= 3",
            lambda getter: getter("a") == [15]
        )

    def test_augmented_asgn_div(self):
        self.assert_transpiled_code_result(
            "a = 5; a //= 3",
            lambda getter: getter("a") == [1]
        )

    def test_augmented_asgn_mod(self):
        self.assert_transpiled_code_result(
            "a = 5; a %= 3",
            lambda getter: getter("a") == [2]
        )

    def test_augmented_asgn_and(self):
        self.assert_transpiled_code_result(
            "a = 0b1100; a &= 0b1010",
            lambda getter: getter("a") == [0b1100 & 0b1010]
        )

    def test_augmented_asgn_or(self):
        self.assert_transpiled_code_result(
            "a = 0b1100; a |= 0b1010",
            lambda getter: getter("a") == [0b1100 | 0b1010]
        )

    def test_augmented_asgn_xor(self):
        self.assert_transpiled_code_result(
            "a = 0b1100; a ^= 0b1010",
            lambda getter: getter("a") == [0b1100 ^ 0b1010]
        )

    def test_augmented_asgn_sl(self):
        self.assert_transpiled_code_result(
            "a = 5; a <<= 3",
            lambda getter: getter("a") == [5 << 3]
        )

    def test_augmented_asgn_plus(self):
        self.assert_transpiled_code_result(
            "a = 12345; a >>= 3",
            lambda getter: getter("a") == [12345 >> 3]
        )

    # multiply operator with lists

    def test_augmented_op_list_times_l(self):
        self.assert_transpiled_code_result(
            "a = 3 * [1, 2, 3, 4]",
            lambda getter: getter("a") == 3 * [1, 2, 3, 4]
        )

    def test_augmented_op_list_times_r(self):
        self.assert_transpiled_code_result(
            "a = [1, 2, 3] * 5",
            lambda getter: getter("a") == [1, 2, 3] * 5
        )

    # programming constructs

    def test_if(self):
        self.assert_transpiled_code_result(
            """
t = True
f = False
a = 2 * [999]
if t:
    a[0] = 1
if f:
    a[1] = 2
""",
            lambda getter: getter("a") == [1, 999]
        )

    def test_ifelse(self):
        self.assert_transpiled_code_result(
            """
t = True
f = False
a = 4 * [999]
if t:
    a[0] = 1
else:
    a[1] = 2

if f:
    a[2] = 3
else:
    a[3] = 4
""",
            lambda getter: getter("a") == [1, 999, 999, 4]
        )

    def test_ifelifelse(self):
        self.assert_transpiled_code_result(
            """
t = True
f = False
a = 11 * [99]
if t:
    a[0] = 1
elif t:
    a[1] = 2
else:
    a[2] = 3

if f:
    a[3] = 4
elif t:
    a[4] = 5
else:
    a[5] = 6

if f:
    a[6] = 7
elif f:
    a[7] = 8
else:
    a[8] = 9

if t:
    a[9] = 10
elif t:
    a[10] = 11
""",
            lambda getter: getter("a") == [1,99,99, 99,5,99, 99,99,9, 10,99]
        )

    def test_while(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
i = 0
while i < len(a):
    a[i] = i + 10
    i += 1
""",
            lambda getter: getter("a") == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        )

    def test_whileelse(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
i = 0
while i < len(a):
    a[i] = i + 10
    i += 1
else:
    a[0] = 88
a[1] = 99
""",
            lambda getter: getter("a") == [88, 99, 12, 13, 14, 15, 16, 17, 18, 19]
        )

    def test_for(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(8):
    a[i] = i + 10
""",
            lambda getter: getter("a") == [10, 11, 12, 13, 14, 15, 16, 17, 0, 0]
        )

    def test_for2(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(3, 8):
    a[i] = i + 10
""",
            lambda getter: getter("a") == [0, 0, 0, 13, 14, 15, 16, 17, 0, 0]
        )

    def test_for3(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(3, 8, 2):
    a[i] = i + 10
""",
            lambda getter: getter("a") == [0, 0, 0, 13, 0, 15, 0, 17, 0, 0]
        )

    def test_for3down(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(8, 2, -3):
    a[i] = i + 10
""",
            lambda getter: getter("a") == [0, 0, 0, 0, 0, 15, 0, 0, 18, 0]
        )

    def test_for2noiter(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(5, 3):
    a[i] = i + 10
""",
            lambda getter: getter("a") == 10 * [0]
        )

    def test_forelse(self):
        self.assert_transpiled_code_result(
            """
a = 10 * [0]
for i in range(8):
    a[i] = i + 10
else:
    a[0] = 88
a[1] = 99
""",
            lambda getter: getter("a") == [88, 99, 12, 13, 14, 15, 16, 17, 0, 0]
        )

    def test_pass(self):
        self.assert_transpiled_code_result(
            """
pass
if True:
    pass
else:
    pass
a = 123
""",
            lambda getter: getter("a") == [123]
        )

    def test_pass_empty(self):
        src_py = "pass"
        src_a = ATranspiler.simple_transpile(src_py).strip()
        self.assertEqual(src_a, "")

    def test_ellipsis_empty(self):
        src_py = "..."
        src_a = ATranspiler.simple_transpile(src_py).strip()
        self.assertEqual(src_a, "")

    def test_fn_ret(self):
        self.assert_transpiled_code_result(
            """
a = f()
def f():
    return 123
""",
            lambda getter: getter("a") == [123]
        )

    def test_fn_local_var(self):
        self.assert_transpiled_code_result(
            """
a = f()
x = 45
def f():
    x = 123
    return x
""",
            lambda getter: getter("a") == [123] and getter("x") == [45]
        )

    def test_fn_local_listvar(self):
        self.assert_transpiled_code_result(
            """
a = f()
x = [1,2,3]
def f():
    x = [4,5]
    return x[0] + x[1]
""",
            lambda getter: getter("a") == [9] and getter("x") == [1,2,3]
        )

    def test_fn_arg(self):
        self.assert_transpiled_code_result(
            """
a = f(123, 45)
def f(x, y):
    return 10 * x + y
""",
            lambda getter: getter("a") == [1275]
        )

    def test_fn_global_var(self):
        self.assert_transpiled_code_result(
            """
x = 45
a = f()
def f():
    global x
    y = [1,2,3]
    x = y[0] + y[1] + y[2]
    return y[2] + 10
""",
            lambda getter: getter("a") == [13] and getter("x") == [6]
        )

    def test_fn_implicit_global_var(self):
        self.assert_transpiled_code_result(
            """
x = 123
a = f()
def f():
    return 10 * x
""",
            lambda getter: getter("a") == [1230]
        )

    def test_fn_thymio_global_var(self):
        self.assert_transpiled_code_result(
            """
a = f()
def f():
    return 10 + temperature + motor_left_speed
""",
            lambda getter: getter("a") == [10]
        )

    def test_onevent(self):
        self.assert_transpiled_code_result(
            """
a = 123
@onevent
def buttons():
    global a
    a = 45
""",
            lambda getter: getter("a") == [45],
            emit="buttons"
        )

    def test_exit(self):
        self.assert_transpiled_code_result(
            """
a = 123
exit(45)
""",
            lambda getter: getter("a") == [123] and getter(None)[0] == [0, [45]]
        )

    def test_bool_in_num(self):
        self.assert_transpiled_code_result(
            """
a = 1
b = a < 5
c = b * 10
""",
            lambda getter: getter("c") == [10]
        )

    def test_num_in_bool(self):
        self.assert_transpiled_code_result(
            """
a = 123
b = a and a > 5
""",
            lambda getter: getter("b") == [1]
        )

    def test_bool_in_list(self):
        self.assert_transpiled_code_result(
            """
a = 10
b = [a < 5, a == 5, a > 5]
""",
            lambda getter: getter("b") == [0, 0, 1]
        )

    def test_boolvar_in_if(self):
        self.assert_transpiled_code_result(
            """
a = 10
b = a < 20
c = 123
if b:
    c = 45
""",
            lambda getter: getter("c") == [45]
        )



if __name__ == '__main__':
    unittest.main()
