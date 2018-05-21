#!/bin/bash
cp -vf ./etc/10-cardioartusb.rules /etc/udev/rules.d/
udevadm control --reload

cp -vf ./etc/*.service /etc/systemd/system/
systemctl daemon-reload