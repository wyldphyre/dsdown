"""Entry point for the dsdown application."""

from dsdown.app import DsdownApp


def main() -> None:
    """Run the dsdown TUI application."""
    app = DsdownApp()
    app.run()


if __name__ == "__main__":
    main()
