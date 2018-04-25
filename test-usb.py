import usb1

c = usb1.USBContext()
devList = c.getDeviceList()

for dev in devList:
    try:
        print '({:x}.{:x}) {:04x}:{:04x}'.format(
            dev.getBusNumber(),
            dev.getDeviceAddress(),
            dev.getVendorID(),
            dev.getProductID()
            )
    except:
        pass
    
