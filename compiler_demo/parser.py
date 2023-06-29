import inspect
from typing import Type

import pyparsing as pp
from pyparsing import pyparsing_common as ppc

from compiler_demo.ast import *


# noinspection PyPep8Naming
def make_parser():
    IF = pp.Keyword('if')
    FOR = pp.Keyword('for')
    WHILE = pp.Keyword('while')
    RETURN = pp.Keyword('return')
    keywords = IF | FOR | RETURN

    # num = ppc.fnumber.copy().setParseAction(lambda s, loc, tocs: tocs[0])
    num = pp.Regex('[+-]?\\d+\\.?\\d*([eE][+-]?\\d+)?')
    # c escape-последовательностями как-то неправильно работает
    str_ = pp.QuotedString('"', escChar='\\', unquoteResults=False, convertWhitespaceEscapes=False)
    literal = num | str_ | pp.Regex('true|false')
    # только, чтобы показать, ~keywords здесь не нужен
    ident = (~keywords + ppc.identifier.copy()).setName('ident')
    type_ = ident.copy().setName('type')

    LPAR, RPAR = pp.Literal('(').suppress(), pp.Literal(')').suppress()
    LBRACK, RBRACK = pp.Literal("[").suppress(), pp.Literal("]").suppress()
    LBRACE, RBRACE = pp.Literal("{").suppress(), pp.Literal("}").suppress()
    LANGLE, RANGLE = pp.Literal("<").suppress(), pp.Literal(">").suppress()
    SEMI, COMMA = pp.Literal(';').suppress(), pp.Literal(',').suppress()
    ASSIGN = pp.Literal('=')

    ADD, SUB = pp.Literal('+'), pp.Literal('-')
    MUL, DIV, MOD = pp.Literal('*'), pp.Literal('/'), pp.Literal('%')
    AND = pp.Literal('&&')
    OR = pp.Literal('||')
    BIT_AND = pp.Literal('&')
    BIT_OR = pp.Literal('|')
    GE, LE, GT, LT = pp.Literal('>='), pp.Literal('<='), pp.Literal('>'), pp.Literal('<')
    NEQUALS, EQUALS = pp.Literal('!='), pp.Literal('==')

    add = pp.Forward()
    expr = pp.Forward()
    stmt = pp.Forward()
    stmt_list = pp.Forward()

    call = ident + LPAR + pp.Optional(expr + pp.ZeroOrMore(COMMA + expr)) + RPAR
    call = ident + LPAR + pp.Optional(expr + pp.ZeroOrMore(COMMA + expr)) + RPAR
    map_ = (pp.Keyword("map").suppress() + LANGLE + type_ + COMMA + type_ + RANGLE + expr).setName('map')
    map_access = (expr + LBRACK + expr + RBRACK + ASSIGN + expr).setName('map_op')

    group = (
        literal |
        call |  # обязательно перед ident, т.к. приоритетный выбор (или использовать оператор ^ вместо | )
        ident |
        LPAR + expr + RPAR
    )

    # обязательно везде pp.Group, иначе приоритет операций не будет работать (см. реализцию set_parse_action_magic);
    # также можно воспользоваться pp.operatorPrecedence (должно быть проще, но не проверял)
    mult = pp.Group(group + pp.ZeroOrMore((MUL | DIV | MOD) + group)).setName('bin_op')
    add << pp.Group(mult + pp.ZeroOrMore((ADD | SUB) + mult)).setName('bin_op')
    compare1 = pp.Group(add + pp.Optional((GE | LE | GT | LT) + add)).setName('bin_op')  # GE и LE первыми, т.к. приоритетный выбор
    compare2 = pp.Group(compare1 + pp.Optional((EQUALS | NEQUALS) + compare1)).setName('bin_op')
    logical_and = pp.Group(compare2 + pp.ZeroOrMore(AND + compare2)).setName('bin_op')
    logical_or = pp.Group(logical_and + pp.ZeroOrMore(OR + logical_and)).setName('bin_op')

    expr << logical_or

    simple_assign = (ident + ASSIGN.suppress() + expr).setName('assign')
    var_inner = simple_assign | ident
    vars_ = type_ + var_inner + pp.ZeroOrMore(COMMA + var_inner)

    assign = ident + ASSIGN.suppress() + expr
    simple_stmt = assign | call

    for_stmt_list0 = (pp.Optional(simple_stmt + pp.ZeroOrMore(COMMA + simple_stmt))).setName('stmt_list')
    for_stmt_list = vars_ | for_stmt_list0
    for_cond = expr | pp.Group(pp.empty).setName('stmt_list')
    for_body = stmt | pp.Group(SEMI).setName('stmt_list')

    if_ = IF.suppress() + LPAR + expr + RPAR + stmt + pp.Optional(pp.Keyword("else").suppress() + stmt)
    while_ = WHILE.suppress() + LPAR + expr + RPAR + stmt
    for_ = FOR.suppress() + LPAR + for_stmt_list + SEMI + for_cond + SEMI + for_stmt_list + RPAR + for_body
    return_ = RETURN.suppress() + expr
    composite = LBRACE + stmt_list + RBRACE

    param = type_ + ident
    params = pp.Optional(param + pp.ZeroOrMore(COMMA + param))
    func = type_ + ident + LPAR + params + RPAR + LBRACE + stmt_list + RBRACE

    stmt << (
        if_ |
        while_ |
        for_ |
        return_ |
        simple_stmt + SEMI |
        map_ |
        map_access |
        # обязательно ниже if, for и т.п., иначе считает их за типы данных (сейчас уже не считает - см. грамматику)
        # обязательно выше vars, иначе посчитает за два vars
        vars_ + SEMI |
        composite |
        func
    )

    stmt_list << (pp.ZeroOrMore(stmt + pp.ZeroOrMore(SEMI)))

    program = stmt_list.ignore(pp.cStyleComment).ignore(pp.dblSlashComment) + pp.StringEnd()

    start = program

    def set_parse_action_magic(rule_name: str, parser_element: pp.ParserElement) -> None:
        if rule_name == rule_name.upper():
            return
        if getattr(parser_element, 'name', None) and parser_element.name.isidentifier():
            rule_name = parser_element.name
        if rule_name in ('bin_op', ):
            def bin_op_parse_action(s, loc, tocs):
                node = tocs[0]
                if not isinstance(node, AstNode):
                    node = bin_op_parse_action(s, loc, node)
                for i in range(1, len(tocs) - 1, 2):
                    second_node = tocs[i + 1]
                    if not isinstance(second_node, AstNode):
                        second_node = bin_op_parse_action(s, loc, second_node)
                    node = BinOpNode(BinOp(tocs[i]), node, second_node, loc=loc)
                return node
            parser_element.setParseAction(bin_op_parse_action)
        elif rule_name == 'map':
            def map_parse_action(s, loc, tocs):
                key_type, value_type, name = tocs[0], tocs[1], tocs[2]
                return MapDeclarationNode(key_type, value_type, name, loc=loc)
            parser_element.setParseAction(map_parse_action)
        elif rule_name == 'map_op':
            def map_access_parse_action(s, loc, tocs):
                name, key_expr, value_expr = tocs[0],tocs[1], tocs[3]
                return MapAccessNode(name, key_expr, value_expr, loc=loc)
            parser_element.setParseAction(map_access_parse_action)
        else:
            cls_name = ''.join(x.capitalize() for x in rule_name.split('_')) + 'Node'
            with suppress(NameError):
                cls: Type = eval(cls_name)
                if not inspect.isabstract(cls):
                    def parse_action(s, loc, tocs):
                        if cls is FuncNode:
                            return FuncNode(tocs[0], tocs[1], tocs[2:-1], tocs[-1], loc=loc)
                        else:
                            return cls(*tocs, loc=loc)
                    parser_element.setParseAction(parse_action)

    for var_name, value in locals().copy().items():
        if isinstance(value, pp.ParserElement):
            set_parse_action_magic(var_name, value)

    return start


parser = make_parser()


def parse(prog: str) -> StmtListNode:
    locs = []
    row, col = 0, 0
    for ch in prog:
        if ch == '\n':
            row += 1
            col = 0
        elif ch == '\r':
            pass
        else:
            col += 1
        locs.append((row, col))

    old_init_action = AstNode.init_action

    def init_action(node: AstNode) -> None:
        loc = getattr(node, 'loc', None)
        if isinstance(loc, int):
            node.row = locs[loc][0] + 1
            node.col = locs[loc][1] + 1

    AstNode.init_action = init_action
    try:
        prog: StmtListNode = parser.parseString(str(prog))[0]
        prog.program = True
        return prog
    finally:
        AstNode.init_action = old_init_action
