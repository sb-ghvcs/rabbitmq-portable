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

if IS_WINDOWS:
  import winreg

script_dir = os.path.dirname(os.path.abspath(__file__))


def check_vc_redist() -> bool:
  if IS_WINDOWS:
    try:
      base_key_path = r"SOFTWARE\\Microsoft\\VisualStudio"
      base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key_path)

      index = 0
      while True:
        try:
          version_key_name = winreg.EnumKey(base_key, index)
          version_key_path = f"{base_key_path}\\{version_key_name}\\VC"
          try:
            vc_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, version_key_path)
            winreg.CloseKey(vc_key)
            print(f"Found VC Redist under version: {version_key_name}")
            break
          except FileNotFoundError:
            pass
          index += 1
        except OSError:
          break
      winreg.CloseKey(base_key)
      return True
    except FileNotFoundError:
      print("VC Redist is not installed.")
      return False
  else:
    raise ValueError("Don't check for vc redist in a non-windows environment")


def install_vc_redist() -> None:
  if IS_WINDOWS:
    print("Installing Bundled VC Redist...")
    erlang_dir = os.path.join(script_dir, "external/erlang")
    vc_redist_installer = os.path.join(erlang_dir, "vc_redist.exe")
    install_command = f'"{vc_redist_installer}" /install /quiet /norestart'
    subprocess.run(["powershell", "-Command", install_command], check=True)
    print("Installed Microsoft Visual C++ Redist")


def set_erlang_env() -> None:
  erts_dir_pattern = "erts-*"
  if IS_WINDOWS:
    erlang_dir = os.path.join(script_dir, "external/erlang")
    absolute_erlang_root_dir = os.path.abspath(erlang_dir)
    if not check_vc_redist():
      install_vc_redist()
    os.environ["ERLANG_HOME"] = absolute_erlang_root_dir
    print(f"Set ERLANG_HOME environment variable to {absolute_erlang_root_dir}")
  else:
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
  print("Starting RabbitMQ server...")
  rabbitmq_process = subprocess.Popen(
    [server_path], stdout=sys.stdout, stderr=sys.stderr
  )
  rabbitmq_process.wait()
  print("Goodbye!")


if __name__ == "__main__":
  main()
