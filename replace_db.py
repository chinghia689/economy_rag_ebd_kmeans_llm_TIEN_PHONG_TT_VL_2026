"""
One-off migration note for SQL placeholder compatibility.

The migration has already been applied in chatbot/utils/base_db.py:
UserDB now defines self.P and uses it in parameterized SQL statements.
This file is kept as a harmless parseable marker instead of an auto-rewrite
script, because regex-based rewrites of Python source are risky.
"""

from pathlib import Path


BASE_DB_PATH = Path(__file__).parent / "chatbot" / "utils" / "base_db.py"


def main() -> None:
    content = BASE_DB_PATH.read_text(encoding="utf-8")
    if 'self.P = "?" if self.db_type == "sqlite" else "%s"' in content:
        print("base_db.py already has SQL placeholder compatibility.")
        return

    raise SystemExit(
        "base_db.py does not contain the expected placeholder compatibility block. "
        "Review manually instead of running a regex rewrite."
    )


if __name__ == "__main__":
    main()
