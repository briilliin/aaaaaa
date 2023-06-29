import sys
import traceback
import os

from compiler_demo import parser
from compiler_demo import semantic_base
from compiler_demo import semantic_checker
from compiler_demo import msil
from compiler_demo import jbc


def execute(prog: str, msil_only: bool = False, jbc_only: bool = False, file_name: str = None) -> None:
    try:
        prog = parser.parse(prog)
    except Exception as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        exit(1)

    if not (msil_only or jbc_only):
        print('ast:')
        print(*prog.tree, sep=os.linesep)

    if not (msil_only or jbc_only):
        print()
        print('semantic-check:')
    try:
        checker = semantic_checker.SemanticChecker()
        scope = semantic_checker.prepare_global_scope()
        checker.semantic_check(prog, scope)
        if not (msil_only or jbc_only):
            print(*prog.tree, sep=os.linesep)
            print()
    except semantic_base.SemanticException as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(2)

    if not (msil_only or jbc_only):
        print()
        print('msil:')
    if not jbc_only:
        try:
            gen = msil.MsilCodeGenerator()
            gen.gen_program(prog)
            print(*gen.code, sep=os.linesep)
        except msil.MsilException or Exception as e:
            print('Ошибка: {}'.format(e.message), file=sys.stderr)
            exit(3)

    if not (msil_only or jbc_only):
        print()
        print('jbc:')
    if not msil_only:
        try:
            gen = jbc.JbcCodeGenerator(file_name)
            gen.gen_program(prog)
            print(*gen.code, sep=os.linesep)
        except jbc.JbcException or Exception as e:
            print('Ошибка: {}'.format(e.message), file=sys.stderr)
            exit(4)
