CARDIOART_VENDOR_ID = 0x10c4
CARDIOART_PRODUCT_ID = 0x8a40

INVALID_PRODUCT_ID = -1
SPO2_PRODUCT_ID = 1
SPO2_PRODUCT_NAME = 'Pulse Oximeter'
ECG_PRODUCT_ID = 2
ECG_PRODUCT_NAME = 'ECG Monitor'
NIBP_PRODUCT_ID = 3

ENDPOINT_ADDRESS = 0x83

def getIdFromProductName(name):
    name = name.lower()
    return {
        ECG_PRODUCT_NAME.lower(): ECG_PRODUCT_ID,
        SPO2_PRODUCT_NAME.lower(): SPO2_PRODUCT_ID
        }.get(name, INVALID_PRODUCT_ID)
