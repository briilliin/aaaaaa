from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Optional, Union, Tuple, Callable

from compiler_demo.semantic_base import TYPE_CONVERTIBILITY, BinOp, \
    TypeDesc, IdentDesc, IdentScope, SemanticException


class AstNode(ABC):
    """Базовый абстрактый класс узла AST-дерева
    """

    init_action: Callable[['AstNode'], None] = None

    def __init__(self, row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__()
        self.row = row
        self.col = col
        for k, v in props.items():
            setattr(self, k, v)
        if AstNode.init_action is not None:
            AstNode.init_action(self)
        self.node_type: Optional[TypeDesc] = None
        self.node_ident: Optional[IdentDesc] = None

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return ()

    def to_str(self):
        return str(self)

    def to_str_full(self):
        r = ''
        if self.node_ident:
            r = str(self.node_ident)
        elif self.node_type:
            r = str(self.node_type)
        return self.to_str() + (' : ' + r if r else '')

    def semantic_error(self, message: str):
        raise SemanticException(message, self.row, self.col)

    """Чтобы среда не "ругалась" в модуле semantic_checker
    """

    def semantic_check(self, checker, scope: IdentScope) -> None:
        checker.semantic_check(self, scope)

    """Чтобы среда не "ругалась" в модуле msil
    """

    def msil_gen(self, generator) -> None:
        generator.msil_gen(self)

    """Чтобы среда не "ругалась" в модуле jbc
    """

    def jbc_gen(self, generator) -> None:
        generator.jbc_gen(self)

    """Чтобы среда не "ругалась" в модуле llvm
    """

    def llvm_gen(self, generator) -> None:
        generator.llvm_gen(self)

    @property
    def tree(self) -> [str, ...]:
        r = [self.to_str_full()]
        childs = self.childs
        for i, child in enumerate(childs):
            ch0, ch = '├', '│'
            if i == len(childs) - 1:
                ch0, ch = '└', ' '
            r.extend(((ch0 if j == 0 else ch) + ' ' + s for j, s in enumerate(child.tree)))
        return tuple(r)

    def __getitem__(self, index):
        return self.childs[index] if index < len(self.childs) else None


class _GroupNode(AstNode):
    """Класс для группировки других узлов (вспомогательный, в синтаксисе нет соотвествия)
    """

    def __init__(self, name: str, *childs: AstNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.name = name
        self._childs = childs

    def __str__(self) -> str:
        return self.name

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return self._childs


class ExprNode(AstNode, ABC):
    """Абстракный класс для выражений в AST-дереве
    """

    pass


class LiteralNode(ExprNode):
    """Класс для представления в AST-дереве литералов (числа, строки, логическое значение)
    """

    def __init__(self, literal: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.literal = literal
        if literal in ('true', 'false'):
            self.value = bool(literal)
        else:
            self.value = eval(literal)

    def __str__(self) -> str:
        return self.literal


class IdentNode(ExprNode):
    """Класс для представления в AST-дереве идентификаторов
    """

    def __init__(self, name: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.name = str(name)

    def __str__(self) -> str:
        return str(self.name)


class TypeNode(IdentNode):
    """Класс для представления в AST-дереве типов данный
       (при появлении составных типов данных должен быть расширен)
    """

    def __init__(self, name: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(name, row=row, col=col, **props)
        self.type = None
        with suppress(SemanticException):
            self.type = TypeDesc.from_str(name)

    def to_str_full(self):
        return self.to_str()


class BinOpNode(ExprNode):
    """Класс для представления в AST-дереве бинарных операций
    """

    def __init__(self, op: BinOp, arg1: ExprNode, arg2: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self) -> str:
        return str(self.op.value)

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return self.arg1, self.arg2


class CallNode(ExprNode):
    """Класс для представления в AST-дереве вызова функций
       (в языке программирования может быть как expression, так и statement)
    """

    def __init__(self, func: IdentNode, *params: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.func = func
        self.params = params

    def __str__(self) -> str:
        return 'call'

    @property
    def childs(self) -> Tuple[IdentNode, ...]:
        return (self.func, *self.params)


class TypeConvertNode(ExprNode):
    """Класс для представления в AST-дереве операций конвертации типов данных
       (в языке программирования может быть как expression, так и statement)
    """

    def __init__(self, expr: ExprNode, type_: TypeDesc,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.expr = expr
        self.type = type_
        self.node_type = type_

    def __str__(self) -> str:
        return 'convert'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (_GroupNode(str(self.type), self.expr),)


def type_convert(expr: ExprNode, type_: TypeDesc, except_node: Optional[AstNode] = None,
                 comment: Optional[str] = None) -> ExprNode:
    """Метод преобразования ExprNode узла AST-дерева к другому типу
    :param expr: узел AST-дерева
    :param type_: требуемый тип
    :param except_node: узел, о которого будет исключение
    :param comment: комментарий
    :return: узел AST-дерева c операцией преобразования
    """

    if expr.node_type is None:
        except_node.semantic_error('Тип выражения не определен')
    if expr.node_type == type_:
        return expr
    if expr.node_type.is_simple and type_.is_simple and \
            expr.node_type.base_type in TYPE_CONVERTIBILITY and type_.base_type in TYPE_CONVERTIBILITY[
        expr.node_type.base_type]:
        return TypeConvertNode(expr, type_)
    else:
        (except_node if except_node else expr).semantic_error('Тип {0}{2} не конвертируется в {1}'.format(
            expr.node_type, type_, ' ({})'.format(comment) if comment else ''
        ))


class StmtNode(ExprNode, ABC):
    """Абстракный класс для деклараций или инструкций в AST-дереве
    """

    def to_str_full(self):
        return self.to_str()


class AssignNode(ExprNode):
    """Класс для представления в AST-дереве оператора присваивания
    """

    def __init__(self, var: IdentNode, val: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.var = var
        self.val = val

    def __str__(self) -> str:
        return '='

    @property
    def childs(self) -> Tuple[IdentNode, ExprNode]:
        return self.var, self.val


class VarsNode(StmtNode):
    """Класс для представления в AST-дереве объявления переменнных
    """

    def __init__(self, type_: TypeNode, *vars_: Union[IdentNode, 'AssignNode'],
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.vars = vars_

    def __str__(self) -> str:
        return str(self.type)

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.vars


class ReturnNode(StmtNode):
    """Класс для представления в AST-дереве оператора return
    """

    def __init__(self, val: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.val = val

    def __str__(self) -> str:
        return 'return'

    @property
    def childs(self) -> Tuple[ExprNode]:
        return (self.val,)


class IfNode(StmtNode):
    """Класс для представления в AST-дереве условного оператора
    """

    def __init__(self, cond: ExprNode, then_stmt: StmtNode, else_stmt: Optional[StmtNode] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    def __str__(self) -> str:
        return 'if'

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return self.cond, self.then_stmt, *((self.else_stmt,) if self.else_stmt else tuple())


class WhileNode(StmtNode):
    """Класс для представления в AST-дереве условного оператора
    """

    def __init__(self, cond: ExprNode, body: Optional[StmtNode],
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.body = body

    def __str__(self) -> str:
        return 'while'

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return self.cond, self.body


class ForNode(StmtNode):
    """Класс для представления в AST-дереве цикла for
    """

    def __init__(self, init: Optional[StmtNode], cond: Optional[ExprNode],
                 step: Optional[StmtNode], body: Optional[StmtNode],
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.init = init if init else EMPTY_STMT
        self.cond = cond if cond else EMPTY_STMT
        self.step = step if step else EMPTY_STMT
        self.body = body if body else EMPTY_STMT

    def __str__(self) -> str:
        return 'for'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.init, self.cond, self.step, self.body


class ParamNode(StmtNode):
    """Класс для представления в AST-дереве объявления параметра функции
    """

    def __init__(self, type_: TypeNode, name: IdentNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.name = name

    def __str__(self) -> str:
        return str(self.type)

    @property
    def childs(self) -> Tuple[IdentNode]:
        return self.name,


class FuncNode(StmtNode):
    """Класс для представления в AST-дереве объявления функции
    """

    def __init__(self, type_: TypeNode, name: IdentNode, params: Tuple[ParamNode], body: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.name = name
        self.params = params
        self.body = body

    def __str__(self) -> str:
        return 'function'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return _GroupNode(str(self.type), self.name), _GroupNode('params', *self.params), self.body


class MapType(StmtNode):
    def __init__(self, key_type: IdentNode, value_type: IdentNode, name: str, row: Optional[int] = None,
                 line: Optional[int] = None, **props):
        super().__init__(row=row, line=line, **props)
        self.key_type = key_type
        self.value_type = value_type
        self.name = name

    @property
    def childs(self) -> Tuple[IdentNode, IdentNode]:
        return self.key_type, self.value_type

    def __str__(self) -> str:
        return f"MapType {self.name}"


class MapDeclarationNode(StmtNode):
    def __init__(self, key_type: IdentNode, value_type: IdentNode, name: str, **props):
        super().__init__(**props)
        self.key_type = key_type
        self.value_type = value_type
        self.name = name

    @property
    def childs(self) -> Tuple[IdentNode, IdentNode]:
        return self.key_type, self.value_type

    def __str__(self) -> str:
        return "map: " + str(self.name)


class MapAccessNode(StmtNode):
    def __init__(self, name: str, key_expr: IdentNode, value_expr: IdentNode, **props):
        super().__init__(**props)
        self.name = name
        self.key_expr = key_expr
        self.value_expr = value_expr

    @property
    def childs(self) -> Tuple[IdentNode, IdentNode]:
        return self.key_expr, self.value_expr

    def __str__(self) -> str:
        return f"{self.name}(map)"


class StmtListNode(StmtNode):
    """Класс для представления в AST-дереве последовательности инструкций
    """

    def __init__(self, *stmts: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.stmts = stmts
        self.program = False

    def __str__(self) -> str:
        return '...'

    @property
    def childs(self) -> Tuple[StmtNode, ...]:
        return self.stmts


EMPTY_STMT = StmtListNode()
EMPTY_IDENT = IdentDesc('', TypeDesc.VOID)
