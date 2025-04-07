=======
``pyl``
=======

Harness the full power of Python in your shell scripts and on the command line.

What is ``pyl``?
================

``pyl`` is a command line tool that let's you write terse but readable shell one-liners
using Python. It does this by introducing a few powerful syntax extensions, described
below.

Why?
====

Python has a super extensive standard library, making it the ultimate shell-scripting
toolbox. The problem is that, while very concise compared to other languages, running
Python snippets from within shell scripts is quite clunky. Consider the following code
that base64-encodes each line of input:

.. code-block:: console

    $ ls | python -c $'import base64, sys\nfor l in sys.stdin: print(base64.b64encode(l.encode()).decode())'
    TElDRU5TRQo=
    UkVBRE1FLnJzdAo=
    cHlwcm9qZWN0LnRvbWwK
    c3JjCg==

The biggest problem with inline Python is whitespace: Python requires newlines and
indentation, and it's not convenient to include those in strings on the command line.

With ``pyl``, the above command becomes:

.. code-block:: console

    $ ls | pyl 'for l in sys::stdin: { base64::b64encode(l.encode()).decode() }'
    TElDRU5TRQo=
    UkVBRE1FLnJzdAo=
    cHlwcm9qZWN0LnRvbWwK
    c3JjCg==

The Solution
============

``pyl`` introduces a number of syntax extensions that, together, make it easy to write
readable shell one-lines that take full advantage of everything Python has to offer:

Braces
    Curly braces that appear immediately after a colon become indentation.

    Example:

    .. code-block:: python

        for i in range(3): { for j in range(4): { print(i * j); } }

    is equivalent to

    .. code-block:: python

        for i in range(3):
            for j in range(4):
                print(i * j)

Line splitting at ``;``
    Lines are split at semicolons.

    In normal Python, statements like ``if`` and ``for`` need to appear on their own
    line. with ``pyl`` you can just use a semicolon:

    Example:

    .. code-block:: python

        import sys; for arg in sys.argv: { print(arg); }

    is equivalent to

    .. code-block:: python

        import sys
        for arg in sys.argv:
            print(arg)

Implicit ``print``
    If a block (either top-level or indented) ends **without** a semicolon, the last
    line is automatically printed (unless the block ends in another block).

    In fact, the whole line is passed as-is to ``print``, so you can pass keyword
    arguments like ``sep``.

    Example:

    .. code-block:: python

        for i in range(10): { i, end='.' }

    is equivalent to

    .. code-block:: python

        for i in range(10):
            print(i, end='.')

Inline-import
    The ``::`` operator can be used to access members of modules without explicitly
    importing them.

    Example:

    .. code-block:: python

        urllib.parse::quote('hello world')

    is equivalent to

    .. code-block:: python

        print(__import__('urllib.parse').parse.quote('hello world'))

Environment variables
    Environment variables can be accessed with ``$NAME``.

    Example:

    .. code-block:: python

        $HOME

    is equivalent to

    .. code-block:: python

        print(__import__('os').environ['HOME'])

Command line arguments
    Command line arguments can be accessed with ``$INDEX`` where ``INDEX`` is a number.

    Example:

    .. code-block:: python

        $1

    is equivalent to

    .. code-block:: python

        print(__import__('sys').argv[1])
