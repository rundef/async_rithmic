import enum

import rithmic.protocol_buffers as pb

class DataType(enum.Enum):
    LAST_TRADE = 1
    BBO = 2

class OrderType(enum.Enum):
    LIMIT = pb.request_new_order_pb2.RequestNewOrder.PriceType.LIMIT
    MARKET = pb.request_new_order_pb2.RequestNewOrder.PriceType.MARKET
    STOP_MARKET = pb.request_new_order_pb2.RequestNewOrder.PriceType.STOP_MARKET

class OrderDuration(enum.Enum):
    DAY = pb.request_new_order_pb2.RequestNewOrder.Duration.DAY
    GTC = pb.request_new_order_pb2.RequestNewOrder.Duration.GTC
    IOC = pb.request_new_order_pb2.RequestNewOrder.Duration.IOC
    FOK = pb.request_new_order_pb2.RequestNewOrder.Duration.FOK

class Gateway(enum.Enum):
    TEST = "rituz00100.rithmic.com:443"

    CHICAGO = "rprotocol.rithmic.com:443"
    SYDNEY = "au.rithmic.com:443"
    SAO_PAULO = "br.rithmic.com:443"
    COLO75 = "colo75.rithmic.com:443"
    FRANKFURT = "de.rithmic.com:443"
    HONGKONG = "hk.rithmic.com:443"
    IRELAND = "ie.rithmic.com:443"
    MUMBAI = "in.rithmic.com:443"
    SEOUL = "kr.rithmic.com:443"
    CAPETOWN = "za.rithmic.com:443"
    TOKYO = "jp.rithmic.com:443"
    SINGAPORE = "sg.rithmic.com:443"
