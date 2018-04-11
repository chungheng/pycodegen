from dis import findlabels, findlinestarts
from opcode import *
from collections import namedtuple

Instruction = namedtuple('Instruction',
    ('line', 'curr_ins', 'jump', 'addr', 'opname', 'arg', 'arg_name'))

class CodeGenerator():
    def __init__(self, func):
        self.func = func
        self.instructions = self.disassemble(func)

        self.var = []
        self.indent = 0
        self.jump_targets = []
        self.enter_indent = False
        self.leave_indent = False

        self.output_statement = self.print_statement

    def _post_output(self):
        self.var = []
        if self.enter_indent:
            self.indent += 4
            self.enter_indent = False
        if self.leave_indent:
            self.indent -= 4
            self.leave_indent = False

    def print_statement(self):
        print (" " * self.indent) + self.var[0]
        self._post_output()

    def generate(self):
        line = -1
        for ins in self.instructions:
            if not len(ins):
                continue
            if ins.line > 0 and line != ins.line:
                if line > 0:
                    self.output_statement()
                line = ins.line

            if ins.jump == ">>":
                if len(self.jump_targets) and self.jump_targets[0] == ins.addr:
                    if len(self.var):
                        self.output_statement()
                    self.jump_targets.pop()
                    self.indent -= 4
                    self.leave_indent = False

            handle = getattr(self, 'handle_' + ins.opname.lower(), None)
            if handle is not None:
                handle(ins)

        self.output_statement()

    def disassemble(self, co, lasti=-1):
        """
        Disassemble a code object.

        This function is modified from the official Python 2.7 dis.disassemble.
        """
        code = co.co_code
        labels = findlabels(code)
        linestarts = dict(findlinestarts(co))
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
                output.append( -1 )

            if i == lasti: output.append( '-->' ),
            else: output.append( '   ' ),
            if i in labels: output.append( '>>' ),
            else: output.append( '  ' ),
            output.append( int(i) ),
            output.append( opname[op] ),
            i = i+1
            if op >= HAVE_ARGUMENT:
                oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
                extended_arg = 0
                i = i+2
                if op == EXTENDED_ARG:
                    extended_arg = oparg*65536L
#                 output.append( repr(oparg).rjust(5) ),
                output.append( int(oparg) )
                if op in hasconst:
                    output.append( repr(co.co_consts[oparg]) ),
                elif op in hasname:
                    output.append( co.co_names[oparg] ),
                elif op in hasjrel:
                    output.append( 'to ' + repr(i + oparg) ),
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

    def handle_load_fast(self, ins):
        self.var.append( ins.arg_name )

    def handle_load_attr(self, ins):
        self.var[-1] += "." + ins.arg_name

    def handle_binary_add(self, ins):
        self.var[-2] = '(%s + %s)' % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_subtract(self, ins):
        self.var[-2] = '(%s - %s)' % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_power(self, ins):
        self.var[-2] = '%s ** %s' % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_multiply(self, ins):
        self.var[-2] = '%s * %s' % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_binary_divide(self, ins):
        self.var[-2] = '%s / %s' % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_compare_op(self, ins):
        op = ins.arg_name
        self.var[-2] = '%s %s %s' % (self.var[-2], op, self.var[-1])
        del self.var[-1]

    def handle_store_attr(self, ins):
        self.var[-1] += "." + ins.arg_name
        self.var[-2] = self.var[-1] + ' = ' + self.var[-2]
        del self.var[-1]

    def handle_store_fast(self, ins):
        tmp = ins.arg_name
        self.var[-1] = tmp + ' = ' + self.var[-1]

    def handle_unary_negative(self, ins):
        self.var[-1] = '-%s' % self.var[-1]

    def handle_pop_jump_if_true(self, ins):
        self.jump_targets.append(ins.arg)
        self.enter_indent = True
        self.var[-1] = 'if not %s:' % self.var[-1]

    def handle_pop_jump_if_false(self, ins):
        self.jump_targets.append(ins.arg)
        self.enter_indent = True
        self.var[-1] = 'if %s:' % self.var[-1]

    def handle_load_global(self, ins):
        self.var.append( ins.arg_name )

    def handle_load_const(self, ins):
        self.var.append( ins.arg_name )

    def handle_dup_top(self, ins):
        self.var.append( self.var[-1] )

    def handle_inplace_add(self, ins):
        self.var[-2] = "(%s + %s)" % (self.var[-2], self.var[-1])
        del self.var[-1]

    def handle_rot_two(self, ins):
        tmp = self.var[-2]
        self.var[-2] = self.var[-1]
        self.var[-1] = tmp

    def handle_pop_top(self, ins):
        pass

    def handle_call_function(self, ins):
        narg = int(ins.arg)
        tmp = "(%s)" % (' %s,'*(narg-1) + ' %s')
        tmp = tmp % tuple(self.var[-narg:])
        self.var[-(narg+1)] += tmp
        del self.var[-narg:]

    def handle_jump_forward(self, ins):
        self.leave_indent = True
        self.output_statement()

        target = int(ins.arg_name.split(' ')[-1])
        old_target = self.jump_targets.pop()

        if target != old_target:
            self.var.append("else:")
            self.enter_indent = True
            self.jump_targets.append(target)

    def handle_return_value(self, ins):
        self.var[-1] = "return %s" % self.var[-1]