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


def set_erlang_env() -> None:
  if IS_WINDOWS:
    erlang_dir = os.path.join(script_dir, "external/erlang")
    absolute_erts_dir = os.path.abspath(erlang_dir)
    os.environ["ERLANG_HOME"] = absolute_erts_dir
  else:
    erts_dir_pattern = "erts-*"
    formed_erts_dir_pattern = os.path.join(
      script_dir, "external/erlang/lib/erlang", erts_dir_pattern
    )
    erts_dir = glob.glob(formed_erts_dir_pattern)
    if len(erts_dir) == 0:
      raise ValueError(f"Could not find erts directory in {formed_erts_dir_pattern}")
    absolute_erts_dir = os.path.join(os.path.abspath(erts_dir[0]), "bin")
    os.environ["PATH"] = absolute_erts_dir + os.pathsep + os.environ["PATH"]


def main() -> None:
  server_dir = os.path.join(script_dir, "external/rabbitmq_server/sbin")
  set_erlang_env()
  if IS_WINDOWS:
    server_path = os.path.join(server_dir, "rabbitmq-server.bat")
  else:
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
