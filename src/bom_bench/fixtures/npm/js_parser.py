"""Tree-sitter based parser for npm reify-case JS files."""

from pathlib import Path

import tree_sitter_javascript as ts_js
from tree_sitter import Language, Node, Parser

JS_LANGUAGE = Language(ts_js.language())


def create_js_parser() -> Parser:
    """Create a tree-sitter parser for JavaScript."""
    parser = Parser(JS_LANGUAGE)
    return parser


def get_node_text(node: Node, source: bytes) -> str:
    """Extract text content from a tree-sitter node."""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def parse_reify_case(js_path: Path) -> dict | None:
    """Parse a reify-case JS file to extract package.json and package-lock.json.

    Returns:
        {
            "name": "fixture-name",
            "package_json": {...},
            "package_lock": {...} | None,
        }
    """
    parser = create_js_parser()
    source = js_path.read_bytes()
    tree = parser.parse(source)

    testdir_obj = _find_testdir_object(tree.root_node, source)
    if not testdir_obj:
        return None

    result = {
        "name": js_path.stem,
        "package_json": None,
        "package_lock": None,
    }

    for key, value in testdir_obj.items():
        if key == "package.json" and isinstance(value, dict):
            result["package_json"] = value
        elif key == "package-lock.json" and isinstance(value, dict):
            result["package_lock"] = value

    return result if result["package_json"] else None


def _find_testdir_object(node: Node, source: bytes) -> dict | None:
    """Find the object passed to t.testdir() call."""
    if node.type == "call_expression":
        callee = node.child_by_field_name("function")
        if callee:
            callee_text = get_node_text(callee, source)
            if "testdir" in callee_text:
                args = node.child_by_field_name("arguments")
                if args:
                    for child in args.children:
                        if child.type == "object":
                            return _parse_testdir_entries(child, source)

    for child in node.children:
        result = _find_testdir_object(child, source)
        if result:
            return result
    return None


def _parse_testdir_entries(node: Node, source: bytes) -> dict:
    """Parse testdir object, handling JSON.stringify() calls for values."""
    result = {}
    for child in node.children:
        if child.type == "pair":
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")
            if key_node and value_node:
                key = get_node_text(key_node, source).strip("\"'")

                if value_node.type == "call_expression":
                    value = _find_json_stringify_arg(value_node, source)
                else:
                    value = _parse_value(value_node, source)

                result[key] = value
    return result


def _find_json_stringify_arg(node: Node, source: bytes) -> dict | None:
    """Find and parse the argument to JSON.stringify() call."""
    if node.type == "call_expression":
        callee = node.child_by_field_name("function")
        if callee and get_node_text(callee, source) == "JSON.stringify":
            args = node.child_by_field_name("arguments")
            if args:
                arg_nodes = [c for c in args.children if c.type not in ("(", ")", ",")]
                if len(arg_nodes) > 0:
                    obj_node = arg_nodes[0]
                    if obj_node.type == "object":
                        return _parse_object_literal(obj_node, source)

    for child in node.children:
        result = _find_json_stringify_arg(child, source)
        if result:
            return result
    return None


def _parse_object_literal(node: Node, source: bytes) -> dict:
    """Parse a JS object literal into a Python dict."""
    result = {}
    for child in node.children:
        if child.type == "pair":
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")
            if key_node and value_node:
                key = get_node_text(key_node, source).strip("\"'")
                value = _parse_value(value_node, source)
                result[key] = value
    return result


def _parse_value(node: Node, source: bytes):
    """Parse a JS value node into Python equivalent."""
    if node.type == "string":
        text = get_node_text(node, source)
        return text[1:-1]
    elif node.type == "number":
        text = get_node_text(node, source)
        return float(text) if "." in text else int(text)
    elif node.type == "true":
        return True
    elif node.type == "false":
        return False
    elif node.type == "null" or node.type == "undefined":
        return None
    elif node.type == "object":
        return _parse_object_literal(node, source)
    elif node.type == "array":
        return [_parse_value(c, source) for c in node.children if c.type not in ("[", "]", ",")]
    elif node.type == "call_expression":
        return _find_json_stringify_arg(node, source)
    return None


def parse_fixture_test_mapping(test_file: Path) -> dict[str, str]:
    """Parse reify.js to map fixture names to test names.

    Correlation:
    - Fixture file: `reify-cases/testing-peer-deps.js`
    - Test in reify.js: `t.test('testing-peer-deps package', ... fixture(t, 'testing-peer-deps') ...)`
    - Snapshot key: `test/arborist/reify.js TAP testing-peer-deps package > expect resolving Promise 1`

    Returns: {"testing-peer-deps": "testing-peer-deps package", ...}
    """
    parser = create_js_parser()
    source = test_file.read_bytes()
    tree = parser.parse(source)
    mapping = {}
    _find_fixture_calls(tree.root_node, source, mapping)
    return mapping


def _find_fixture_calls(node: Node, source: bytes, mapping: dict) -> None:
    """Recursively find fixture() calls within t.test() calls.

    Looks for patterns like:
    t.test('test name', async t => {
        ...
        fixture(t, 'fixture-name')
        ...
    })
    """
    if node.type == "call_expression":
        callee = node.child_by_field_name("function")
        if callee and "t.test" in get_node_text(callee, source):
            args = node.child_by_field_name("arguments")
            if args:
                arg_nodes = [c for c in args.children if c.type not in ("(", ")", ",")]
                if len(arg_nodes) >= 1:
                    test_name_node = arg_nodes[0]
                    if test_name_node.type == "string":
                        test_name = get_node_text(test_name_node, source)[1:-1]

                        for child in node.children:
                            fixture_name = _find_fixture_name_in_node(child, source)
                            if fixture_name:
                                mapping[fixture_name] = test_name
                                break

    for child in node.children:
        _find_fixture_calls(child, source, mapping)


def _find_fixture_name_in_node(node: Node, source: bytes) -> str | None:
    """Find fixture(t, 'name') call and extract fixture name."""
    if node.type == "call_expression":
        callee = node.child_by_field_name("function")
        if callee and get_node_text(callee, source) == "fixture":
            args = node.child_by_field_name("arguments")
            if args:
                arg_nodes = [c for c in args.children if c.type not in ("(", ")", ",")]
                if len(arg_nodes) >= 2:
                    name_node = arg_nodes[1]
                    if name_node.type == "string":
                        return get_node_text(name_node, source)[1:-1]

    for child in node.children:
        result = _find_fixture_name_in_node(child, source)
        if result:
            return result
    return None
