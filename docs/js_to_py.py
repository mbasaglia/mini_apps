import pathlib

import esprima


def comment_to_docstring(indent, node, comments, comment_start):
    comment = comments.get(comment_start or node.range[0])

    if not comment:
        return ""

    docstring = indent + '"""\n'

    lines = comment.splitlines()

    for i, line in enumerate(lines):
        line = line.strip("\t *")
        line = line.replace("@", "\\")
        line = line.replace("\\brief ", "")
        if (i == 0 or i == len(lines)-1) and line == "":
            continue
        docstring += indent + line + "\n"

    docstring += indent + '"""\n'

    return docstring


def js2py_body(node, indent, comments, all):
    src = ""

    for child in node.body:
        src += js2py(child, indent, comments, all) + "\n"

    return src.rstrip()


def js2py_param(node):
    if node.type == "Identifier":
        return node.name
    elif node.type == "AssignmentPattern":
        return js2py_param(node.left) + "=" + js2py_param(node.right)
    elif node.type == "Literal":
        return str(node.value)


def js2py_import(specifier):
    local = specifier.local.name
    imported = specifier.imported.name
    if local != imported:
        return "%s as %s" % (imported, local)
    return imported


def js_process_comments(tree, source):
    comments = {}

    for comment in tree.comments:
        end = comment.range[1]+1
        while end < len(source) and source[end].isspace():
            end += 1
        comments[end] = comment.value

    return comments


def js2py(node, indent, comments, all, comment_start=None):
    if node.type == "Program":
        src = js2py_body(node, indent, comments, all)
        if all:
            src = "__all__ = %r\n\n%s\n" % (all, src)

        return src

    elif node.type == "ExportNamedDeclaration":
        all.append(node.declaration.id.name)

        return js2py(node.declaration, indent, comments, all, node.range[0])

    elif node.type == "ClassDeclaration":

        src = "%sclass %s" % (indent, node.id.name)
        if node.superClass:
            src += "(%s):\n" % node.superClass.name
            if node.superClass.name == "EventTarget":
                src = "class EventTarget:\n    pass\n\n" + src
        else:
            src += ":\n"

        indent += " " * 4
        src += comment_to_docstring(indent, node, comments, comment_start)
        src += "\n"
        src += js2py_body(node.body, indent, comments, all)
        return src

    elif node.type == "MethodDefinition":
        value = node.value
        src = indent
        if value.isAsync:
            src += "async "

        name = node.key.name
        if name == "constructor":
            name = "__init__"
        src += "def %s(self" % name

        if value.params:
            src += ", " + ", ".join(map(js2py_param, value.params))

        src += "):\n"
        indent += " " * 4
        src += comment_to_docstring(indent, node, comments, comment_start)
        src += indent + "pass\n"
        return src

    elif node.type == "ImportDeclaration":
        src = indent
        src += "from "
        module = node.source.value.rsplit(".", 1)[0].replace("/", ".")
        if module.startswith(".."):
            module = module[1:]

        src += module + " import " + ", ".join(map(js2py_import, node.specifiers))
        return src + "\n"

    return ""


def js_file_to_py(source):
    tree = esprima.parseModule(source, {"comment": True, "range": True})
    comments = js_process_comments(tree, source)
    return js2py(tree, "", comments, [])
