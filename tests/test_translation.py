import unittest
from pathlib import Path
import tempfile

from pocketport.translation import IRValidationError, execute, emit_c, parse, verify_host, write_c

REPO = Path(__file__).resolve().parent.parent
IR = REPO / "examples/translation-demo/score.ppir"


class TranslationTests(unittest.TestCase):
    def test_parser_and_interpreter(self):
        program = parse(IR.read_text())
        self.assertEqual(program.name, "score_bonus")
        self.assertEqual(execute(program, 1, 2), 9)
        self.assertEqual(execute(program, 0xffffffff, 1), 0)

    def test_host_recompiler_matches_reference(self):
        self.assertEqual(verify_host(parse(IR.read_text()))["vectors_passed"], 4)

    def test_codegen_committed_files_are_reproducible(self):
        head, code = emit_c(parse(IR.read_text()))
        generated = REPO / "examples/source-port/generated"
        self.assertEqual((generated / "score.h").read_text(), head)
        self.assertEqual((generated / "score.c").read_text(), code)
        with tempfile.TemporaryDirectory() as folder:
            h, c = write_c(parse(IR.read_text()), Path(folder))
            self.assertEqual(h.read_text(), head)
            self.assertEqual(c.read_text(), code)

    def test_unknown_instruction_rejected(self):
        with self.assertRaisesRegex(IRValidationError, "Unsupported"):
            parse("func x a\nsyscall b a\nret a\nend")

    def test_unresolved_operand_rejected(self):
        with self.assertRaises(IRValidationError):
            parse("func x a\nadd b a unknown\nret b\nend")

    def test_reassignment_rejected(self):
        with self.assertRaises(IRValidationError):
            parse("func x a\nconst a 2\nret a\nend")

    def test_invalid_constants_rejected(self):
        with self.assertRaises(IRValidationError):
            parse("func x a\nconst b 4294967296\nret b\nend")

    def test_missing_return_rejected(self):
        with self.assertRaises(IRValidationError):
            parse("func x a\nconst b 2\nend")
