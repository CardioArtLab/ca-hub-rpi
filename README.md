# ca-hub-rpi
Raspberry Pi (v3) Hub Service for USB-to-Bluetooth via ZeroMQ
Licensed to CardioArtLab (Academic works)

## Installation
- clone project at `/opt`
```sh
$ cd /opt
```
- install systemd service and udev
```sh
$ ./install.sh
$ systemctl enable ca-hub-rpi
$ systemctl start ca-hub-rpi
```
## Functions
- When USB bus=1 address=2 plug in, systemd will start `ca-hub-rpi@1:2`
- Main service logging
```sh
$ journalctl -u ca-hub-rpi -r | head -20
$ journalctl -u ca-hub-rpi@[bus]:[address] -r | head -20
```

- Bluetooth config
```sh
$ hciconfig
```