import configparser
import os
import glob
import sys
import subprocess
import signal
from types import FrameType
from typing import Optional, no_type_check


class UnsupportedOS(Exception):
  ...


class CaseSensitiveConfigParser(configparser.ConfigParser):
  def optionxform(self, optionstr: str) -> str:
    return optionstr


# Check execution environment
IS_WINDOWS = "nt" in str(os.name).lower()
IS_LINUX = "posix" in str(os.name).lower()
if not (IS_WINDOWS or IS_LINUX):
  raise UnsupportedOS(
    f"Unsupported OS: {os.name}. Currently only windows (nt) and linux (posix) are supported."
  )

if IS_WINDOWS:
  # pylint: disable-next=import-error
  import winreg

script_dir = os.path.dirname(os.path.abspath(__file__))


@no_type_check
def check_vc_redist() -> bool:
  """
  Check if Microsoft Visual C++ Redist package is installed.

  On Windows, check registry key HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/VisualStudio
  and look for any version key (e.g. 14.0, 15.0, etc.) with a child key named "VC".
  If such a key is found, print a message and return True. If no such key is found,
  print a message and return False.

  On non-Windows platforms, raise ValueError.

  Returns:
    bool: True if VC Redist is installed, False otherwise.
  """
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
  """
  Install the bundled Microsoft Visual C++ Redist package.

  This package is only installed on Windows if the vc_redist.exe installer is
  present in the external/erlang directory, and the package is not already
  installed.

  The package is installed in quiet mode with no restart required. The
  installation is verified by checking the return code of the subprocess.
  """
  if IS_WINDOWS:
    print("Installing Bundled VC Redist...")
    erlang_dir = os.path.join(script_dir, "external/erlang")
    vc_redist_installer = os.path.join(erlang_dir, "vc_redist.exe")
    install_command = f'"{vc_redist_installer}" /install /quiet /norestart'
    subprocess.run(["powershell", "-Command", install_command], check=True)
    print("Installed Microsoft Visual C++ Redist")


def set_erlang_env() -> str:
  """
  Set Erlang environment variables and update erl.ini in the erts directory.

  On Windows, the ERLANG_HOME environment variable is set to the absolute path of
  the external/erlang directory. The erl.ini file is updated with absolute paths
  to the bin directory and the root directory.

  On Linux, the PATH environment variable is set to include the bin directory of
  the erts directory. This allows the Erlang executables to be found without
  setting ERLANG_HOME.

  Returns the absolute path to the bin directory of the erts directory.
  """
  erts_dir_pattern = "erts-*"
  if IS_WINDOWS:
    erlang_dir = os.path.join(script_dir, "external/erlang")
    absolute_erlang_root_dir = os.path.abspath(erlang_dir)
    if not check_vc_redist():
      install_vc_redist()
    os.environ["ERLANG_HOME"] = absolute_erlang_root_dir
    print(f"Set ERLANG_HOME environment variable to {absolute_erlang_root_dir}")
    # Update erl.ini in erts dir
    formed_erts_dir_pattern = os.path.join(absolute_erlang_root_dir, erts_dir_pattern)
    erts_dir = glob.glob(formed_erts_dir_pattern)
    if len(erts_dir) == 0:
      raise ValueError(f"Could not find erts directory in {formed_erts_dir_pattern}")
    absolute_erts_bin_dir = os.path.join(os.path.abspath(erts_dir[0]), "bin")
    erl_ini = os.path.join(absolute_erts_bin_dir, "erl.ini")
    config = CaseSensitiveConfigParser()
    config.read(erl_ini)
    config["erlang"]["Bindir"] = absolute_erts_bin_dir.replace("\\", "\\\\")
    config["erlang"]["Rootdir"] = absolute_erlang_root_dir.replace("\\", "\\\\")
    with open(erl_ini, "w", encoding="utf-8") as configfile:
      config.write(configfile)
    print("Updated erl.ini")
  else:
    formed_erts_dir_pattern = os.path.join(
      script_dir, "external/erlang/lib/erlang", erts_dir_pattern
    )
    erts_dir = glob.glob(formed_erts_dir_pattern)
    if len(erts_dir) == 0:
      raise ValueError(f"Could not find erts directory in {formed_erts_dir_pattern}")
    absolute_erts_bin_dir = os.path.join(os.path.abspath(erts_dir[0]), "bin")
    os.environ["PATH"] = absolute_erts_bin_dir + os.pathsep + os.environ["PATH"]
  return absolute_erts_bin_dir


def main() -> None:
  server_dir = os.path.join(script_dir, "external/rabbitmq_server/sbin")
  erts_bin_dir = set_erlang_env()
  if IS_WINDOWS:
    server_path = os.path.join(server_dir, "rabbitmq-server.bat")
    epmd_path = os.path.join(erts_bin_dir, "epmd.exe")
  else:
    server_path = os.path.join(server_dir, "rabbitmq-server")
    epmd_path = os.path.join(erts_bin_dir, "epmd")

  def signal_handler(_signum: int, _frame: Optional[FrameType]) -> None:
    print("SIGINT received. Shutting down RabbitMQ server")
    if rabbitmq_process:
      rabbitmq_process.terminate()

  signal.signal(signal.SIGINT, signal_handler)

  # Start rabbitmq server
  print("Starting RabbitMQ server...")
  rabbitmq_process = subprocess.Popen(
    [server_path, "--name=rabbit@localhost"],
    stdout=sys.stdout,
    stderr=sys.stderr,
    shell=True,
  )
  rabbitmq_process.wait()
  print("Stopping EPMD process...")
  subprocess.run([epmd_path, "-kill"], check=True, shell=True)
  print("Goodbye!")


if __name__ == "__main__":
  main()
