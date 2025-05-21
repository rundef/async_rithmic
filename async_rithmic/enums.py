import enum

from . import protocol_buffers as pb

class DataType(int, enum.Enum):
    LAST_TRADE = 1
    BBO = 2

OrderType = pb.request_new_order_pb2.RequestNewOrder.PriceType
OrderDuration = pb.request_new_order_pb2.RequestNewOrder.Duration
TransactionType = pb.request_new_order_pb2.RequestNewOrder.TransactionType

LastTradePresenceBits = pb.last_trade_pb2.LastTrade.PresenceBits
BestBidOfferPresenceBits = pb.best_bid_offer_pb2.BestBidOffer.PresenceBits

ExchangeOrderNotificationType = pb.exchange_order_notification_pb2.ExchangeOrderNotification.NotifyType

TimeBarType = pb.request_time_bar_replay_pb2.RequestTimeBarReplay.BarType

InstrumentType = pb.request_search_symbols_pb2.RequestSearchSymbols.InstrumentType
SearchPattern = pb.request_search_symbols_pb2.RequestSearchSymbols.Pattern

class Gateway(str, enum.Enum):
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
