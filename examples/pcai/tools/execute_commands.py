from chainless import Tool

import os
import traceback


@Tool.tool(
    name="execute_commands",
    description=(
        "A mini interactive command interface. The user can run Python expressions "
        "or terminal commands here. Features:\n"
        "- 'cls' : clears the screen\n"
        "- 'quit': closes the interface\n"
        "- 'help': shows available commands\n"
        "- Python code: print statements, calculations, variable assignments, etc.\n"
        "- Terminal commands: dir, ls, echo, etc."
    ),
)
def execute_commands(start: bool = True) -> None:
    """
    Mini interactive command interface.

    The user can run both Python expressions and terminal commands.
    """
    print("Mini Command Interface Started. Use 'help' to see available commands.")
    env = {}  # Local dictionary for Python code execution

    while start:
        try:
            user_input = input(">>> ").strip()
            lower_input = user_input.lower()

            if lower_input == "cls":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            elif lower_input == "quit":
                print("Exiting program...")
                break
            elif lower_input == "help":
                print(
                    "Available commands:\n"
                    "- cls : clears the screen\n"
                    "- quit: closes the interface\n"
                    "- help: shows this message\n"
                    "- Python expressions: print(2+2), x=5, x*2, for/if blocks\n"
                    "- Terminal commands: dir, ls, echo, etc."
                )
                continue

            # Try running as Python code first
            try:
                # Try evaluating a single-line Python expression
                try:
                    eval_result = eval(user_input, env)
                    if eval_result is not None:
                        print(eval_result)
                    continue
                except SyntaxError:
                    # If not a simple expression, try exec for multi-line code
                    exec(user_input, env)
                    continue
            except Exception:
                traceback.print_exc()

            # If not Python, try executing as a terminal command
            try:
                result = os.popen(user_input).read()
                if result.strip():
                    print(result)
            except Exception as e:
                print(f"Failed to execute terminal command: {e}")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting...")
            break
