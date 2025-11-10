"""Entry point for running trading_bot as a module."""

import sys

if len(sys.argv) > 1 and sys.argv[1] == "tui":
    from trading_bot.tui import main

    main()
else:
    from trading_bot.cli import cli

    cli()
