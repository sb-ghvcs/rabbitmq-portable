import os
import glob
import sys
import subprocess
import signal
from types import FrameType
from typing import Optional


class UnsupportedOS(Exception):
  ...


# Check execution environment
IS_WINDOWS = "nt" in str(os.name).lower()
IS_LINUX = "posix" in str(os.name).lower()
if not (IS_WINDOWS or IS_LINUX):
  raise UnsupportedOS(
    f"Unsupported OS: {os.name}. Currently only windows (nt) and linux (posix) are supported."
  )

script_dir = os.path.dirname(os.path.abspath(__file__))


def get_erlang_path() -> str:
  erts_dir_pattern = "erts-*"
  if IS_WINDOWS:
    erlang_dir = os.path.join(script_dir, "external/erlang")
    absolute_erts_dir = os.path.abspath(erlang_dir)
  else:
    formed_erts_dir_pattern = os.path.join(
      script_dir, "external/erlang/lib/erlang", erts_dir_pattern
    )
    erts_dir = glob.glob(formed_erts_dir_pattern)
    if len(erts_dir) == 0:
      raise ValueError(f"Could not find erts directory in {formed_erts_dir_pattern}")
    absolute_erts_dir = os.path.abspath(erts_dir[0])
  return absolute_erts_dir


def main() -> None:
  server_dir = os.path.join(script_dir, "external/rabbitmq_server/sbin")
  erlang_dir = get_erlang_path()
  if IS_WINDOWS:
    # set ERLANG_HOME variable
    os.environ["ERLANG_HOME"] = erlang_dir
    server_path = os.path.join(server_dir, "rabbitmq-server.bat")
  else:
    # Append erlang to path
    sys.path.append(erlang_dir)
    server_path = os.path.join(server_dir, "rabbitmq-server")

  def signal_handler(_signum: int, _frame: Optional[FrameType]) -> None:
    print("SIGINT received. Shutting down RabbitMQ server")
    if rabbitmq_process:
      rabbitmq_process.terminate()

  signal.signal(signal.SIGINT, signal_handler)

  # Start rabbitmq server
  rabbitmq_process = subprocess.Popen(
    [server_path], stdout=sys.stdout, stderr=sys.stderr
  )
  rabbitmq_process.wait()
  print("RabbitMQ server shutdown. Goodbye!")


if __name__ == "__main__":
  main()
