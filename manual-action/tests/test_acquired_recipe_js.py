"""Generated literal snippets only; no source archive, runtime or network use."""
import json
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acquired_recipe_js import UnsupportedJavaScript, parse_recipe_javascript


class StaticRecipeJavaScriptTests(unittest.TestCase):
    def test_source_fields_ratios_forks_and_process_nodes(self):
        raw = '''// Synthetic recipe, never actual source content.
        export default {
          repoId: 'generated', parentRepoId: null, slug: 'generated-stew',
          title: 'Generated stew', author: 'fixture-author',
          ingredients: [{name: 'beans', ratioValue: 1.25,
            defaultUnit: 'part', role: 'base',},],
          processNodes: [{instructions: 'Mix. Then serve.', active: true}],
          activeTime: 5, totalTime: 1.00e+2,
        };
        '''
        row = parse_recipe_javascript(raw)
        self.assertEqual(row['ingredients'][0]['ratioValue'], 1.25)
        self.assertEqual(row['ingredients'][0]['defaultUnit'], 'part')
        self.assertEqual(row['processNodes'][0]['instructions'], 'Mix. Then serve.')
        self.assertIsNone(row['parentRepoId'])
        self.assertIs(row['processNodes'][0]['active'], True)
        self.assertEqual(row['totalTime'], 100)

    def test_exact_wrappers_and_bom_comments(self):
        body = '{title:"Generated", ingredients:[], steps:[]}'
        wrappers = [body, body + ';', 'export default ' + body,
                    'module.exports = ' + body + ';',
                    'const recipe = ' + body + '; export default recipe;',
                    'const $recipe_1 = ' + body + '\nmodule.exports = $recipe_1']
        for wrapped in wrappers:
            with self.subTest(wrapped=wrapped):
                row = parse_recipe_javascript('\ufeff/* fixture */\n' + wrapped + ' // done')
                self.assertEqual(row['title'], 'Generated')

    def test_strings_escapes_unicode_and_plain_templates(self):
        raw = r'''export default {one:'Chef\'s "cup"',
          two:"\x41\u00e9\u{1f375}\ud83d\ude00", three:`Line
one`, four:`literal \${not_code}`, five:"\b\f\n\r\t\v\0\\\/"}'''
        row = parse_recipe_javascript(raw)
        self.assertEqual(row['one'], 'Chef\'s "cup"')
        self.assertEqual(row['two'], 'Aé🍵😀')
        self.assertEqual(row['three'], 'Line\none')
        self.assertEqual(row['four'], 'literal ${not_code}')
        self.assertEqual(row['five'], '\b\f\n\r\t\v\0\\/')
        json.dumps(row, ensure_ascii=False).encode('utf-8')

    def test_template_crlf_and_escaped_newline(self):
        row = parse_recipe_javascript('{a:`one\r\ntwo\rthree`,b:"one\\\r\ntwo"}')
        self.assertEqual(row, {'a': 'one\ntwo\nthree', 'b': 'onetwo'})

    def test_literals_in_comments_not_interpreted(self):
        raw = '// throw new Error();\r\nexport /* import danger */ default {title:"/*literal*/",x: false};// ${danger}'
        self.assertEqual(parse_recipe_javascript(raw), {'title': '/*literal*/', 'x': False})

    def test_numeric_values(self):
        row = parse_recipe_javascript('{a:-2,b:0,c:1.,d:.5,e:-1e-2,f:1E+2}')
        self.assertEqual(row, {'a': -2, 'b': 0, 'c': 1., 'd': .5, 'e': -.01, 'f': 100.})

    def test_dynamic_or_ambiguous_syntax_rejected(self):
        snippets = [
            'import x from "x"; export default {}',
            'export default fn()', 'export default Object.freeze({})',
            'export default {x: process.exit()}', '{x: require("fs")}',
            '{...other}', '{x:[...other]}', '{["x"]:1}', '{get x(){return 1}}',
            '{set x(v){}}', '{x(){}}', '{x:()=>1}', '{x:function(){}}',
            '{x: new Date()}', '{x: another}', '{x: undefined}', '{x: NaN}',
            '{x: Infinity}', '{x:-Infinity}', '{x: 1+2}', '{x:+2}',
            '{x: /regex/}', '{x: 0xff}', '{x: 01}', '{x: 1_000}', '{x: 1n}',
            '{x: `before ${danger()} after`}', '{x:`${1}`} ',
            'const x={}; x.title="changed"; export default x',
            'const x={}; export default y', 'let x={}; export default x',
            'const x={}, y={}; export default x', 'const x={}; export default {x}',
            'export default {}; attack()', 'export default {}; {}',
            '({x:1})', '{x}', '{x:[,1]}', '{x:[1,,2]}', '{x:1,,}',
            'export const recipe={}', 'module["exports"]={}',
        ]
        for snippet in snippets:
            with self.subTest(snippet=snippet), self.assertRaises(UnsupportedJavaScript):
                parse_recipe_javascript(snippet)

    def test_duplicate_and_prototype_keys_rejected(self):
        for snippet in ('{x:1,x:2}', '{x:1,"x":2}', '{__proto__: {}}',
                        '{x:{"constructor":"x"}}', '{prototype:null}',
                        r'{"\u005f_proto__":null}'):
            with self.subTest(snippet=snippet), self.assertRaises(UnsupportedJavaScript):
                parse_recipe_javascript(snippet)

    def test_bad_strings_comments_and_numbers_rejected(self):
        for snippet in ('{x:"unfinished}', '{x:"line\nbreak"}', '{x:1} /* missing',
                        r'{x:"\ud800"}', r'{x:"\udfff"}', r'{x:"\u{110000}"}',
                        r'{x:"\u12xx"}', r'{x:"\xG0"}', r'{x:"\01"}',
                        r'{x:"\8"}', r'{x:"\q"}', '{x:1e999}', '{x:1e}',
                        '{x:1.2.3}', '{x:`unfinished}', '{x:"\ud800"}'):
            with self.subTest(snippet=repr(snippet)), self.assertRaises(UnsupportedJavaScript):
                parse_recipe_javascript(snippet)

    def test_resource_caps(self):
        for kwargs in ({'max_source_bytes': 7}, {'max_tokens': 3}, {'max_depth': 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(UnsupportedJavaScript):
                parse_recipe_javascript('{x:{y:[1,2]}}', **kwargs)
        with self.assertRaises(UnsupportedJavaScript):
            parse_recipe_javascript('{x:"éé"}', max_source_bytes=9)
        with self.assertRaises(UnsupportedJavaScript):
            parse_recipe_javascript('{x:' + '[' * 80 + '0' + ']' * 80 + '}')

    def test_limit_validation(self):
        for kwargs in ({'max_tokens': 0}, {'max_depth': False}, {'max_source_bytes': '4'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                parse_recipe_javascript('{}', **kwargs)

    def test_long_number_is_bounded_independent_of_python_int_limit(self):
        with self.assertRaises(UnsupportedJavaScript):
            parse_recipe_javascript('{x:' + '9' * 300 + '}')

    def test_generated_json_roundtrip(self):
        rng = random.Random(20261022)
        atoms = [None, False, True, -3, 0, 1.25, 'é🍵', "Chef's cup",
                 '${literal}', 'slash\\newline\n', '']
        for _ in range(250):
            row = {'title': rng.choice(atoms), 'values': [rng.choice(atoms) for _ in range(10)],
                   'nested': {'first': rng.choice(atoms), 'second': rng.randrange(-100, 100)}}
            raw = json.dumps(row, ensure_ascii=rng.choice((False, True)))
            self.assertEqual(parse_recipe_javascript('export default ' + raw), row)

    def test_many_comments_do_not_change_literal(self):
        raw = '// generated comment\n' * 10000 + 'export default {title:"Generated"}'
        self.assertEqual(parse_recipe_javascript(raw), {'title': 'Generated'})

    def test_root_object_required(self):
        for snippet in ('export default []', 'export default null', 'export default "x"',
                        'const recipe=[]; export default recipe;'):
            with self.subTest(snippet=snippet), self.assertRaises(UnsupportedJavaScript):
                parse_recipe_javascript(snippet)

    def test_deterministic_and_sanitized_failure_messages(self):
        self.assertEqual(parse_recipe_javascript('{z:[1,{a:"x"}]}'),
                         parse_recipe_javascript('{z:[1,{a:"x"}]}'))
        try:
            parse_recipe_javascript('{x: secret_fixture_token}')
        except UnsupportedJavaScript as exc:
            self.assertNotIn('secret_fixture_token', str(exc))
        else:
            self.fail('Unsupported identifier unexpectedly parsed')


if __name__ == '__main__':
    unittest.main()
