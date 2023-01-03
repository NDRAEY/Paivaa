import ast
from pprint import pprint

VAR = []

def error(msg: str):
    print("\x1b[31mERROR\x1b[0m:", msg)

def pytype2c(pytype: str):
    if pytype == "str": return "unsigned char[]"
    elif pytype == "int": return "ssize_t"
    elif pytype == "float": return "double"
    elif pytype == "bool": return "bool"
    elif pytype == None: return "void"
    else: return pytype

def wrap(typ: str, val):
    if typ == "str":
        return '"'+str(val)+'"'
    elif typ == "int":
        return str(val)
    elif typ == "bool":
        return "true" if val else "false"
    else:
        return str(val)

def argsdef2c(args):
    total = ""
    
    for arg in args:
        ann = arg.annotation.id if arg.annotation else None
        pytype = pytype2c(ann)
        
        if ann == "str":
            pytype = pytype[:-2]
            arg.arg += "[]"
        total += f"{pytype} {arg.arg}, "

    return total[:-2]

def op2c(op) -> str:
    if type(op) is ast.Add: return "+"
    elif type(op) is ast.Sub: return "-"
    elif type(op) is ast.Mult: return "*"
    elif type(op) is ast.Lt: return "<"
    elif type(op) is ast.Eq: return "=="
    elif type(op) is ast.Gt: return ">"
    else: return "?"

def get_value_ast(val):
    if type(val) is ast.Name:
        return val.id
    elif type(val) is ast.Constant:
        return wrap(type(val.value).__name__, val.value)
    else:
        error("Unknown type to left compare operator: %s (get_value_ast())" % type(val).__name__)
        exit(1)

def compare2c(comp):
    l = comp.left
    ops = comp.ops  # List?
    r = comp.comparators  # Why it's a list?

    total = ""

    '''
    if type(l) is ast.Name:
        total += l.id
    elif type(l) is ast.Constant:
        total += wrap(type(l.value).__name__, l.value)
    else:
        error("Unknown type to left compare operator: %s" % type(l).__name__)
    '''
    total += get_value_ast(l)

    total += f" {op2c(ops[0])} "

    if len(r) > 1:
        error("Only supported single Compare.Comparators (error, because comparators > 1)")
        exit(1)

    r = r[0]  # Remoce when support multi-comparators

    '''
    if type(r) is ast.Name:
        total += r.id
    elif type(r) is ast.Constant:
        total += wrap(type(r.value).__name__, r.value)
    else:
        error("Unknown type to right compare operator: %s" % type(r).__name__)
    '''

    total += get_value_ast(r)

    return total

def evaluate_binop(binop: ast.BinOp):
    l = binop.left
    op = binop.op
    r = binop.right

    '''
    if not ((type(l) is ast.Constant) and (type(r) is ast.Constant)):  # To be rewritten
        error("Now only can evaluate two constants, not: %s and %s" % \
              (type(l).__name__, type(r).__name__))
        exit(1)
    '''

    if (type(l) is ast.Constant) and (type(r) is ast.Constant):
        lt = type(l.value).__name__
        rt = type(r.value).__name__

        if lt == rt:
            ty = op2c(op)
            
            if ty == "+":
                res = l.value + r.value
            elif ty == "*":
                res = l.value * r.value
            elif ty == "/":
                res = l.value / r.value
            elif ty == "-":
                res = l.value - r.value
            else:
                error("Unsupported BinOp operation: %s", type(op).__name__)
                exit(1)
            return wrap(type(res).__name__, res)
    else:
        return str(get_value_ast(l)) + op2c(op) + str(get_value_ast(r))

def find_var(name, additional = []):
    for i in VAR+additional:
        if i[0] == name:
            return i

def args2c(args) -> str:
    a = ""

    for i in args:
        if type(i) is ast.Constant:
            a += wrap(type(i.value).__name__, i.value)+", "
        elif type(i) is ast.Name:
            a += i.id+", "
        elif type(i) is ast.BinOp:
            a += evaluate_binop(i)+", "
        else:
            print("Args: ", args)
            print("On: ", i)
            error("Unknown type %s in args2c(...)" % type(i))
            exit(1)
    
    return a[:-2]

def pytype2cfmt(typ):
    if typ == "str":
        return "%s"
    elif typ == "int":
        return "%d"

def handle_func(name, args, varargs = []):
    if name == "print":
        typ = ""
        addargs = ""
        print_end = "\\n"
        print_sep = " "

        if len(args) == 0:
            return f'printf(\"{print_end}\")'

        for i in args:
            if type(i) is ast.Constant:
                v = i.value
                '''
                if type(v).__name__ == "str":
                    typ += "%s"
                elif type(v).__name__ == "int":
                    typ += "%d"
                '''
                typ += pytype2cfmt(type(v).__name__)

                addargs += wrap(type(v).__name__, v)
                typ += print_sep
                addargs += ", "
            elif type(i) is ast.Name:
                v = i.id
                tp = pytype2cfmt(find_var(v, additional=varargs)[1])

                addargs += v + ", "
                typ += tp + print_sep
            else:
                error("Unknown type for argument handling: %s" % type(i).__name__)
                exit(1)
                
        typ = typ[:-len(print_sep)]
        addargs = addargs[:-2]

        total = f"printf(\"{typ}{print_end}\", {addargs})"
        return total
    else:
        '''
        error("Unhandled function: %s" % name)
        exit(1)
        '''
        return f"{name}({args2c(args)})"

def args2vars(args):
    va = []

    for i in args:
        va.append((i.arg, i.annotation.id))

    return va

def convert2c(ast_body, create_main: bool = True, only_main: bool = False, main_return: int = 0, args_prog = []) ->  str:
    functiondefs = [i for i in ast_body if type(i) is ast.FunctionDef]
    main = [i for i in ast_body if not (type(i) is ast.FunctionDef)]

    headers = "#include <stdint.h>\n" + \
              "#include <sys/types.h>\n" + \
              "#include <stdio.h>\n" + \
              "#include <stdbool.h>\n"
    otherblocks = headers
    mainblock = ""

    for i in main:
        if type(i) is ast.AnnAssign:
            target = i.target
            t = pytype2c(i.annotation.id)
            val = i.value
            cassign = None
            vname = target.id

            if i.annotation.id == "str":
                vname += "[]"
                t = t[:-2]

            if type(val) is ast.BinOp:
                cassign = evaluate_binop(val)
            else:
                cassign = wrap(i.annotation.id, val.value)

            if type(target) is ast.Name:
                otherblocks += t + " " + vname + " = " + cassign + ";\n"
            else:
                error("Unknown type %s while parsing assignment in left hand" % type(target))
                exit(1)
            VAR.append((target.id, i.annotation.id))
        elif type(i) is ast.While:
            test = i.test
            body = i.body

            if type(test) is ast.Compare:
                test = compare2c(test)
            elif type(test) is ast.Constant:
                test = wrap(type(test.value).__name__, test.value)

            mainblock += f"while({test}) " + "{\n"+convert2c(body, only_main=True)+"}\n"
            # exit(1)
        elif type(i) is ast.Expr:  # How to parse it?
            expval = i.value

            if type(expval) is ast.Call:
                fname = expval.func.id
                fargs = expval.args

                handled = handle_func(fname, fargs, varargs=args_prog)

                fcall = f"{fname}({args2c(fargs)});"
                # print("!!!: ", handled, "vs.", fcall)
                mainblock += handled+";\n"
            else:
                error("Unknown Expr value type: %s", type(expval))
                exit(1)
        elif type(i) is ast.AugAssign:
            targ = i.target
            op = i.op
            val = i.value

            total = f"{get_value_ast(targ)} {op2c(op)}= {get_value_ast(val)};\n"

            mainblock += total
        elif type(i) is ast.If:
            test = i.test
            body = i.body
            orelse = i.orelse

            stest = compare2c(test)
            sbody = convert2c(body, only_main=True)
            sorelse = convert2c(orelse, only_main=True)

            mainblock += f"if({stest}) " + "{\n"+sbody+"}\n"
            if len(sorelse)!=0:
                mainblock += "else{\n"+sorelse+"}\n"
        elif type(i) is ast.Pass:
            pass
        else:
            error("Unknown AST element: %s" % type(i))
            exit(1)

    for i in functiondefs:
        name = i.name
        args = i.args.args
        argvars = args2vars(args)
        body = i.body
        rettype = i.returns.id if i.returns else None

        fblk = f"{pytype2c(rettype)} {name}({argsdef2c(args)})" + \
            "{\n"+convert2c(body, create_main=False, only_main=True, args_prog=argvars)+"}"

        otherblocks += fblk

    if only_main:
        return mainblock
        
    main_ = ("int main() {\n"+mainblock+"\n}" if create_main else "")
    return otherblocks + "\n" + main_

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog='paivaa',
        description='Toy Python to ANSI C converter!'
    )

    parser.add_argument("file", type=str)

    args = parser.parse_args()

    filename = args.file

    with open(filename, "r") as f:
        tree = ast.parse(f.read())
        print(ast.dump(tree))

        c_code = convert2c(tree.body)

        print("Code:")
        print(c_code)

        with open('.'.join(filename.split(".")[:-1])+".c", "w") as wf:
            wf.write(c_code)
            wf.close()
        f.close()
