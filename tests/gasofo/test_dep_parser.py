from unittest import TestCase
# ====== uncomment the following to test old regex based parser ====
# import os
# os.environ['GASOFO_USE_OLD_DEP_PARSER'] = "1"

from gasofo.dep_parser import parse_deps_used


class TestParseDepsUsed(TestCase):

    def test_can_parse_deps(self):
        def dummy(self):
            v = self.deps.a() + self.deps.b()
            return v + self.deps.c()

        self.assertEqual({'a', 'b', 'c'}, parse_deps_used(dummy))

    def test_can_have_duplicate_deps(self):
        def dummy(self):
            v = self.deps.a(1) + self.deps.a(2) + self.deps.b() + self.deps.b()
            return v + self.deps.c()

        self.assertEqual({'a', 'b', 'c'}, parse_deps_used(dummy))

    def test_case_sensitive(self):
        def dummy(self):
            self.deps.aa()
            self.deps.aA()
            self.deps.Aa()
            self.deps.AA()

        self.assertEqual({'aa', 'aA', 'Aa', 'AA'}, parse_deps_used(dummy))

    def test_can_parse_deps_with_args_and_kwargs(self):
        def dummy(self):
            v = self.deps.a(1, 2, 3) + self.deps.b(4, five=5)
            return v + self.deps.c(v)

        self.assertEqual({'a', 'b', 'c'}, parse_deps_used(dummy))

    def test_not_affected_by_other_method_calls(self):
        def dummy(self):
            self.deps.yes()
            self.no1()
            blah.self.deps.no2()
            blah.deps.no3()
            no4()
            no5().no6().no7()

        self.assertEqual({'yes'}, parse_deps_used(dummy))

    def test_not_affected_by_ref_that_is_not_a_call(self):
        def dummy(self):
            self.deps.yes()
            blah(self.deps.not_a_call)

        self.assertEqual({'yes'}, parse_deps_used(dummy))

    def test_not_affected_by_calls_in_comments(self):
        def dummy(self):
            self.deps.yes()
            # self.deps.no()

        self.assertEqual({'yes'}, parse_deps_used(dummy))

    def test_not_affected_by_calls_in_string_literals(self):
        def dummy(self):
            self.deps.yes()
            a = "self.deps.no1()"
            b = "blah blah self.deps.no2() blab lah"
            c = """
            self.deps.no3()
            """

        self.assertEqual({'yes'}, parse_deps_used(dummy))

    def test_can_handle_chained_calls(self):
        def dummy(self):
            return self.deps.a().append(1)

        self.assertEqual({'a'}, parse_deps_used(dummy))

    def test_can_handle_calls_within_args_and_kwargs(self):
        def dummy(self):
            return self.deps.a(
                self.deps.b(self.deps.c(self.deps.d())),
                another=self.deps.e(),
                more=''.join(self.deps.f())
            )

        self.assertEqual({'a', 'b', 'c', 'd', 'e', 'f'}, parse_deps_used(dummy))

    def test_can_handle_calls_in_ops(self):
        def dummy(self):
            a = ('a' * self.deps.a()).split(self.deps.b())
            return a or self.deps.c() and self.deps.d()

        self.assertEqual({'a', 'b', 'c', 'd'}, parse_deps_used(dummy))

    def test_deps_can_be_in_branch_condition(self):
        def dummy(self):
            if blah() or self.deps.a():
                return self.deps.b()
            elif self.deps.c():
                return self.deps.d()
            else:
                return self.deps.e()

        self.assertEqual({'a', 'b', 'c', 'd', 'e'}, parse_deps_used(dummy))

    def test_can_handle_comprehension_syntax(self):
        def dummy(self):
            dict_comp = {self.deps.d1(i): self.deps.d2(i) for i in self.deps.d3() if self.deps.d4(i)}
            set_comp = {self.deps.s1(i) for i in self.deps.s2() if self.deps.s3(i)}
            list_comp = [self.deps.L1(i) for i in self.deps.L2() if self.deps.L3(i)]
            gen_comp = (self.deps.g1(i) for i in self.deps.g2() if self.deps.g3(i))

        self.assertEqual({
            'd1', 'd2', 'd3', 'd4',
            's1', 's2', 's3',
            'L1', 'L2', 'L3',
            'g1', 'g2', 'g3',
        }, parse_deps_used(dummy))

    def test_also_captures_calls_in_inner_functions(self):
        """ Technically calls within a nested function should not count since there is no guarantee that will be called,
            but then again, there's no guarantee anything will be called at runtime (e.g. with branches) since we're
            merely doing a static parse.

            Anyway, we do "cheat" in this manner with partials so we allow for now.
        """
        def dummy(self):
            v = self.deps.a()

            def inner_dummy(*args, **kwargs):
                return self.deps.b(metadata=True, *args, **kwargs)

            return self.deps.a(func=inner_dummy)

        self.assertEqual({'a', 'b'}, parse_deps_used(dummy))



