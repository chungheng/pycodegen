from __future__ import print_function

import dis
from opcode import *
from collections import namedtuple

import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    Instruction = namedtuple('Instruction',
        ('starts_line', 'curr_ins', 'is_jump_target', 'offset', 'opname', 'arg', 'argval'))

class CodeGenerator(object):
    def __init__(self, func, **kwargs):
        self.ostream = kwargs.pop('ostream', sys.stdout)
        self.indent = kwargs.pop('indent', 4)
        self.offset = kwargs.pop('offset', 0)
        self.newline = kwargs.pop('newline', '\n')

        self.func = func
        self.instructions = self.get_instructions(func)

        self.var = []
        self.space = 0
        self.jump_targets = []
        self.enter_indent = False
        self.leave_indent = False

    def _post_output(self):
        self.var = []
        if self.enter_indent:
            self.space += self.indent
            self.enter_indent = False
        if self.leave_indent:
            self.space -= self.indent
            self.leave_indent = False

    def output_statement(self):
        spaces = " " * (self.offset + self.space)
        for statement in self.var:
            self.ostream.write(spaces + statement + self.newline)
        self._post_output()

    def generate(self, instructions=None):
        instructions = instructions or self.instructions
        line = -1
        for ins in instructions:
            if not len(ins):
                continue
            if ins.starts_line is not None and line != ins.starts_line:
                if line > 0 and len(self.var):
                    self.output_statement()
                line = ins.starts_line

            if ins.is_jump_target:
                self.process_jump(ins)

            handle = getattr(self, "handle_{}".format(ins.opname.lower()), None)
            if handle is not None:
                handle(ins)
            else:
                print(ins)

        self.output_statement()

    def get_instructions(self, co, lasti=-1):
        """
        Get the bytecode instructions of a code object.

        This function is modified from the official Python 2.7 dis.disassemble.
        """
        # python3
        if sys.version_info[0] == 3:
            return [x for x in dis.get_instructions(co)]

        # python2
        code = co.co_code
        labels = dis.findlabels(code)
        linestarts = dict(dis.findlinestarts(co))
        n = len(code)
        i = 0
        extended_arg = 0
        free = None
        output = []
        instructions = []

        while i < n:
            c = code[i]
            op = ord(c)
            if i in linestarts:
                if i > 0:
                    instructions.append([])
                    output = []
                output.append( int(linestarts[i]) )
            else:
                output.append( None )

            if i == lasti: output.append( '-->' ),
            else: output.append( '   ' ),

            # determine if jump target
            output.append( i in labels )
            output.append( int(i) ),
            output.append( opname[op] ),
            i = i+1
            if op >= HAVE_ARGUMENT:
                oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
                extended_arg = 0
                i = i+2
                if op == EXTENDED_ARG:
                    extended_arg = oparg*65536
#                 output.append( repr(oparg).rjust(5) ),
                output.append( int(oparg) )
                if op in hasconst:
                    output.append( co.co_consts[oparg] ),
                elif op in hasname:
                    output.append( co.co_names[oparg] ),
                elif op in hasjrel:
                    output.append( i + oparg ),
                elif op in haslocal:
                    output.append( co.co_varnames[oparg] ),
                elif op in hascompare:
                    output.append( cmp_op[oparg] ),
                elif op in hasfree:
                    if free is None:
                        free = co.co_cellvars + co.co_freevars
                    output.append( free[oparg] ),
            for j in xrange(max(0, 7-len(output))):
                output.append('')

            ins = Instruction(*output)
            instructions.append(ins)
            output = []
        return instructions

    def process_jump(self, ins):
        if len(self.jump_targets) and self.jump_targets[0] == ins.offset:
            if len(self.var):
                self.output_statement()
            self.jump_targets.pop()
            self.space -= self.indent
            self.leave_indent = False
            self.var.append('')
            self.output_statement()

    def handle_load_fast(self, ins):
        self.var.append( ins.argval )

    def handle_load_attr(self, ins):
        self.var[-1] += ".{0}".format(ins.argval)

    def handle_store_subscr(self, ins):
        temp = "{0}[{1}] = {2}"
        self.var[-3] = temp.format(self.var[-2], self.var[-1], self.var[-3])
        del self.var[-2:]

    # Binary operation
    def handle_binary_power(self, ins):
        self.var[-2] = "{0} ** {1}".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_multiply(self, ins):
        self.var[-2] = "({0} * {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_matrix_multiply(self, ins):
        raise TypeError("BINARY_MATRIX_MULTIPLY is not supported.")

    def handle_binary_floor_divide(self, ins):
        self.var[-2] = "({0} / {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_divide(self, ins):
        self.var[-2] = "({0} / {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_true_divide(self, ins):
        self.var[-2] = "({0} / {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_modulo(self, ins):
        self.var[-2] = "({0} % {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_add(self, ins):
        self.var[-2] = "({0} + {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_subtract(self, ins):
        self.var[-2] = "({0} - {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_subscr(self, ins):
        self.var[-2] = "{0}[{1}]".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_lshift(self, ins):
        self.var[-2] = "({0} << {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_rshift(self, ins):
        self.var[-2] = "({0} >> {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_and(self, ins):
        self.var[-2] = "({0} & {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_xor(self, ins):
        self.var[-2] = "({0} ^ {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_or(self, ins):
        self.var[-2] = "({0} | {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    # in-place operation
    def handle_inplace_power(self, ins):
        pass

    def handle_inplace_multiply(self, ins):
        pass

    def handle_inplace_matrix_multiply(self, ins):
        raise TypeError("BINARY_MATRIX_MULTIPLY is not supported.")

    def handle_inplace_floor_divide(self, ins):
        pass

    def handle_inplace_divide(self, ins):
        pass

    def handle_inplace_true_divide(self, ins):
        pass

    def handle_inplace_modulo(self, ins):
        pass

    def handle_inplace_add(self, ins):
        self.var[-2] = "({0} + {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_inplace_subtract(self, ins):
        self.var[-2] = "({0} - {1})".format(self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_inplace_subscr(self, ins):
        pass

    def handle_inplace_lshift(self, ins):
        pass

    def handle_inplace_rshift(self, ins):
        pass

    def handle_inplace_and(self, ins):
        pass

    def handle_inplace_xor(self, ins):
        pass

    def handle_inplace_or(self, ins):
        pass

    def handle_store_subscr(self, ins):
        pass

    def handle_delete_subscr(self, ins):
        pass

    def handle_compare_op(self, ins):
        op = ins.argval
        self.var[-2] = "({0} {1} {2})".format(self.var[-2], op, self.var[-1])
        del self.var[-1]

    def handle_store_attr(self, ins):
        self.handle_load_attr(ins)
        self.var[-2] = "{0} = {1}".format(self.var[-1], self.var[-2])
        del self.var[-1]

    def handle_store_fast(self, ins):
        self.var[-1] = "{0} = {1}".format(ins.argval, self.var[-1])

    def handle_unary_negative(self, ins):
        self.var[-1] = "(-{0})".format(self.var[-1])

    def handle_pop_jump_if_true(self, ins):
        self.jump_targets.append(ins.arg)
        self.enter_indent = True
        self.var[-1] = "if not {0}:".format(self.var[-1])

    def handle_pop_jump_if_false(self, ins):
        self.jump_targets.append(ins.arg)
        self.enter_indent = True
        self.var[-1] = "if {0}:".format(self.var[-1])

    def handle_load_global(self, ins):
        self.var.append( ins.argval )

    def handle_load_const(self, ins):
        self.var.append( ins.argval )

    def handle_dup_top(self, ins):
        self.var.append( self.var[-1] )

    def handle_rot_two(self, ins):
        tmp = self.var[-2]
        self.var[-2] = self.var[-1]
        self.var[-1] = tmp

    def handle_pop_top(self, ins):
        pass

    def handle_call_function(self, ins):
        narg = int(ins.arg)
        args = [] if narg == 0 else [str(x) for x in self.var[-narg:]]
        self.var[-(narg+1)] += "({})".format(', '.join(args))

        if narg > 0:
            del self.var[-narg:]

    def handle_jump_forward(self, ins):
        self.leave_indent = True
        self.output_statement()

        target, old_target = ins.argval, self.jump_targets.pop()

        if target != old_target:
            self.var.append("else:")
            self.enter_indent = True
            self.jump_targets.append(target)
        else:
            self.var.append('')
            self.output_statement()

    def handle_return_value(self, ins):
        self.var[-1] = "return {0}".format(self.var[-1])
