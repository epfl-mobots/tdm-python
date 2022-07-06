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

    def assert_transpiled_code_result(self, src_py, assertTrueFun):
        """Transpile Python code, compile it, execute it on a vm and
        execute assertTrueFun(var_getter)
        """
        print("src_py", src_py)
        src_a = ATranspiler.simple_transpile(src_py)
        print("src_a", src_a)
        c = AsebaCompiler()
        bc, variable_descriptions = c.compile(src_a)
        v = AsebaVM()
        v.set_bytecode(bc)
        v.run()

        def getter(name):
            val = v.get_variable(name, variable_descriptions)
            print("getter", name, val)
            return val

        b = assertTrueFun(getter)
        self.assertTrue(b)

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

if __name__ == '__main__':
    unittest.main()
