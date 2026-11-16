import ast
import json
import os
import pathlib
import re
import unittest
import tinycss2

ROOT = pathlib.Path(__file__).parent
SOURCE = ROOT / os.environ.get('SCANNER_SOURCE', 'source')
CSS = (SOURCE / 'shelf-scanner-inline.css').read_text()
SYSTEM = (SOURCE / 'offmenu-system.css').read_text()

def active(query, width, height):
    conditions = re.findall(r'\((min|max)-(width|height):\s*(\d+)px\)', query)
    if not conditions:
        return False
    return all((width if axis == 'width' else height) >= int(n) if bound == 'min' else (width if axis == 'width' else height) <= int(n) for bound, axis, n in conditions)

def styles(selectors, width, height):
    found = {}
    priority = {}
    sequence = 0
    def visit(rules):
        nonlocal sequence
        for rule in rules:
            if rule.type == 'at-rule' and rule.content:
                if rule.lower_at_keyword == 'media' and active(tinycss2.serialize(rule.prelude), width, height):
                    visit(tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True))
            elif rule.type == 'qualified-rule':
                sequence += 1
                matched = [s.strip() for s in tinycss2.serialize(rule.prelude).split(',') if s.strip() in selectors]
                if not matched:
                    continue
                specificity = max((s.count('#'), s.count('.') + s.count('[')) for s in matched)
                for declaration in tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True):
                    if declaration.type != 'declaration':
                        continue
                    rank = (declaration.important, specificity, sequence)
                    if rank >= priority.get(declaration.name, (-1, (), -1)):
                        priority[declaration.name] = rank
                        found[declaration.name] = tinycss2.serialize(declaration.value).strip()
    for content in [SYSTEM, CSS]:
        visit(tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True))
    return found

def number(expression, width, height, variables=None, safe=0):
    variables = variables or {}
    def evaluate(value):
        tokens = tinycss2.parse_component_value_list(value)
        def group(tokens):
            pieces = [[]]
            for token in tokens:
                if token.type == 'literal' and token.value == ',':
                    pieces.append([])
                else:
                    pieces[-1].append(token)
            return [tinycss2.serialize(p).strip() for p in pieces]
        output = ''
        for token in tokens:
            if token.type == 'function':
                args = group(token.arguments)
                if token.lower_name == 'env':
                    v = safe if args[0] == 'safe-area-inset-bottom' else 0
                elif token.lower_name == 'var':
                    v = variables.get(args[0], evaluate(args[1]))
                elif token.lower_name == 'calc':
                    v = evaluate(args[0])
                elif token.lower_name in ['min', 'max']:
                    v = (min if token.lower_name == 'min' else max)(evaluate(a) for a in args)
                else:
                    raise AssertionError('Unsupported source expression: ' + value)
                output += str(v)
            elif token.type == 'dimension':
                output += str(token.value * {'px': 1, 'vw': width / 100, 'dvh': height / 100}[token.lower_unit])
            else:
                output += tinycss2.serialize([token])
        tree = ast.parse(output.strip(), mode='eval')
        def arithmetic(node):
            if isinstance(node, ast.Expression): return arithmetic(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                a, b = arithmetic(node.left), arithmetic(node.right)
                return a + b if isinstance(node.op, ast.Add) else a - b
            raise AssertionError('Unsupported arithmetic: ' + output)
        return arithmetic(tree)
    return evaluate(expression)

GUIDE = {'.scanner-approved .capture-guide', '.capture-guide'}
SHEET = {'.scanner-approved .product-sheet', '.scanner-approved .product-sheet[data-snap="0"]'}

class Geometry(unittest.TestCase):
    def test_short_portrait_collapsed_sheet_is_outside_guide_with_existing_fallback(self):
        guide = styles(GUIDE, 360, 480)
        sheet = styles(SHEET, 360, 480)
        occupied = number(sheet['bottom'], 360, 480) + number(sheet['height'], 360, 480)
        bottom = number(guide['bottom'], 360, 480)
        self.assertGreaterEqual(bottom, occupied, 'Guide extends under the actual collapsed sheet/footer CSS')
        self.assertGreaterEqual(480 - number(guide['top'], 360, 480) - bottom, 48)

    def test_short_portrait_retains_existing_sheet_occlusion_variable_contract(self):
        guide = styles(GUIDE, 360, 480)
        bottom = number(guide['bottom'], 360, 480, {'--sheet-occlusion': 64})
        self.assertEqual(bottom, 64 + 58 + 12)
        self.assertEqual(number(guide['top'], 360, 480), 82)

    def test_short_portrait_safe_area_and_expanded_sheet_contract(self):
        guide = styles(GUIDE, 390, 480)
        bottom = number(guide['bottom'], 390, 480, {'--sheet-occlusion': 120}, safe=34)
        self.assertEqual(bottom, 120 + 58 + 34 + 12)
        self.assertGreaterEqual(480 - 82 - bottom, 48)

    def test_tall_portrait_reservation_is_preserved(self):
        guide = styles(GUIDE, 390, 844)
        self.assertEqual(number(guide['bottom'], 390, 844, {'--sheet-occlusion': 200}), 270)
        self.assertEqual(number(guide['top'], 390, 844), 126)

    def test_wide_short_screen_keeps_existing_side_sheet_clearance(self):
        guide = styles(GUIDE, 800, 480)
        right = number(guide['right'], 800, 480)
        self.assertEqual(right, min(460, .43 * 800) + 30)
        self.assertEqual(number(guide['bottom'], 800, 480), 80)
        self.assertGreaterEqual(right - (min(460, .43 * 800) + 14), 16)

    def test_actual_markup_binds_the_styled_guide_to_existing_capture_element(self):
        from html.parser import HTMLParser
        class Elements(HTMLParser):
            def __init__(self): super().__init__(); self.items = []
            def handle_starttag(self, tag, attrs): self.items.append((tag, dict(attrs)))
        parser = Elements(); parser.feed((SOURCE / 'shelf-scanner.html.excerpt.html').read_text())
        self.assertEqual(len([a for _, a in parser.items if a.get('id') == 'capture-guide' and a.get('class') == 'capture-guide']), 1)
        self.assertEqual(len([a for tag, a in parser.items if tag == 'video' and a.get('id') == 'video']), 1)
        self.assertEqual(styles(GUIDE, 360, 480)['pointer-events'], 'none')

if __name__ == '__main__':
    unittest.main(verbosity=2)
