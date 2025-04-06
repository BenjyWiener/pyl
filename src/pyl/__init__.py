"""Bringing the power of Python to shell one-liners."""

from collections.abc import Sequence
import optparse
import sys
import token
from typing import cast

from macro_polo import Token, lex, stringify
from macro_polo.macros import LoopingMacro, MultiMacro, ScanningMacro
from macro_polo.match import MacroMatch
from macro_polo.parse import parse_macro_matcher, parse_macro_transcriber


_braces_matcher = parse_macro_matcher(': { $($inner:tt)* }')
_braces_inner_transcriber = parse_macro_transcriber('$($inner)*')
_braces_transcriber = parse_macro_transcriber(': $> $($inner)* $<')


def braces_macro(tokens: Sequence[Token]) -> tuple[Sequence[Token], int]:
    """Replace braces with indentation.

    Replaces ``: {...}`` with an indented block preceded by ``:``.
    """
    if match := _braces_matcher.match(tokens):
        inner_tokens = tuple(_braces_inner_transcriber.transcribe(match.captures))

        inner_tokens = line_macro(inner_tokens) or inner_tokens
        output = tuple(_braces_transcriber.transcribe({'inner': list(inner_tokens)}))
        return output, match.size

    return (), 0


_line_matcher = parse_macro_matcher(
    # Semicolon terminated lines.
    '$( $($[!;] $line:tt)* ;)*'
    # Optional non-semicolon-terminated line.
    # tokens.
    '$('
    '  $('
    #    Only match if the line does not contain any indents.
    '    $[!$> $($_:tt)* $<]'
    #    Only match if the line doesn't contain braces that will become indents.
    '    $[!: {$($_:tt)*}]'
    '    $print_line:tt'
    '  )+'
    #  Only match if the line matches all remaining tokens.
    '  $[!$_:tt]'
    ')?'
)
_line_transcriber = parse_macro_transcriber(
    '$($($line)* $^)* $(print($($print_line)*))*'
)


def line_macro(tokens: Sequence[Token]) -> Sequence[Token] | None:
    """Replace semicolons with newlines and expand implicit print.

    A non-semicolon-terminated line at the end of a block becomes an implicit print
    statement (unless it contains an indented block itself).
    """
    if match := _line_matcher.match(tokens):
        return (*_line_transcriber.transcribe(match.captures), *tokens[match.size :])

    return None


_short_import_matcher = parse_macro_matcher('$mod:name $(.$submod:name)* ::')
_short_import_transcriber = parse_macro_transcriber('__import__($modpath)$(.$submod)*.')


def short_import_macro(tokens: Sequence[Token]) -> tuple[Sequence[Token], int]:
    """Expand short import syntax.

    Replaces :samp:`{mod}.{submod1}.{submod2}::{member}` with
    :samp:`__import__('{mod}.{submod1}.{submod2}').{submod1}.{submod2}.{member}`.
    """
    match _short_import_matcher.match(tokens):
        case MacroMatch(
            size=size,
            captures={
                'mod': Token(string=mod),
                'submod': submod_capture,
            } as captures,
        ):
            modpath = mod
            if isinstance(submod_capture, list):
                submodpath = '.'.join(
                    tok.string for tok in cast(list[Token], submod_capture)
                )
                modpath += f'.{submodpath}'

            modpath_token = Token(token.STRING, repr(modpath))

            return tuple(
                _short_import_transcriber.transcribe(
                    {**captures, 'modpath': modpath_token}
                )
            ), size

    return (), 0


_env_var_matcher = parse_macro_matcher('$$ $name:name')
_env_var_transcriber = parse_macro_transcriber("__import__('os').environ[$namestr]")


def env_var_macro(tokens: Sequence[Token]) -> tuple[Sequence[Token], int]:
    """Replace ``$NAME`` with environment variable lookup.

    Replaces :samp:`${NAME}` with :samp:`__import__('os').environ['{NAME}']`.
    """
    match _env_var_matcher.match(tokens):
        case MacroMatch(
            size=size,
            captures={'name': Token(string=namestr)},
        ):
            namestr_token = Token(token.STRING, repr(namestr))
            return tuple(
                _env_var_transcriber.transcribe({'namestr': namestr_token})
            ), size

    return (), 0


_argv_matcher = parse_macro_matcher('$$ $index:number')
_argv_transcriber = parse_macro_transcriber("__import__('sys').argv[$index]")


def argv_macro(tokens: Sequence[Token]) -> tuple[Sequence[Token], int]:
    """Replace ``$INDEX`` with argv indexing.

    Replaces :samp:`${INDEX}` with :samp:`__import__('sys').argv[{INDEX}]`.
    """
    if match := _argv_matcher.match(tokens):
        return tuple(_argv_transcriber.transcribe(match.captures)), match.size

    return (), 0


pyl_macro = MultiMacro(
    LoopingMacro(
        ScanningMacro(
            braces_macro,
            short_import_macro,
            env_var_macro,
            argv_macro,
        ),
    ),
    line_macro,
)


def main() -> None:
    """Process command line arguments."""
    optparser = optparse.OptionParser(
        'usage: %prog [options] script [args...]',
    )
    optparser.add_option(
        '--expand',
        action='store_true',
        default=False,
        help='Print expanded script and exit.',
    )
    optparser.disable_interspersed_args()

    opts, args = optparser.parse_args()

    if len(args) < 1:
        optparser.print_help()
        sys.exit(1)

    expand_only: bool = opts.expand
    script: str = args.pop(0)
    sys.argv[1:] = args

    tokens = tuple(lex(script))
    expanded_tokens = pyl_macro(tokens)
    expanded_script = stringify(
        expanded_tokens if expanded_tokens is not None else tokens
    )

    if expand_only:
        print(expanded_script)
        sys.exit(0)

    compiled_script = compile(expanded_script, '<expanded script>', 'exec')

    exec(compiled_script)
