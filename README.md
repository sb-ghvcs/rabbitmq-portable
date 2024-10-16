# RabbitMQ Portable

This repository contains automated workflows to build portable installations of RabbitMQ, along with Erlang, so you can avoid installing them as system dependencies. 

**Tested for Linux and Windows only**

The inspiration was quickly getting up and running with RabbitMQ for Celery. I was experimenting with small scale distributed applications and saw that there is no portable version of RabbitMQ or Erlang. For the simple need of running a server quickly on a single node, there seemed to be a lot of system-wide installation involved. 

This would particularly be helpful if you need to test your applications running on RabbitMQ locally, but do not have admin access on your laptop (corporate laptop?) and want to get up and running quickly.

Simply download the latest release from the releases section for your platform.

## How It Works

We build Erlang from source, since erlang doesn't provide a portable zip. We build the linux release on ubuntu runners and windows release on windows runners.

Then, we download rabbitmq's binaries (zip for windows, tar.xf for linux), unpack it, put it in a directory with erlang, and have a start script that takes care of setting any env variables needed for running it. We then package everything with PyInstaller into a single executable.

## Last run Inputs:
OpenSSL Windows URL: https://slproweb.com/download/Win64OpenSSL-3_3_2.exe
