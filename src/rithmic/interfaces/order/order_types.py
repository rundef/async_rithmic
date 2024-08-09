import abc
import enum
from datetime import datetime as dt
from typing import Union, List, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame

from rithmic.tools.general import get_utc_now
from rithmic.tools.pyrithmic_exceptions import UncancellableOrderException, UnmodifiableOrderException


class FillStatus(enum.Enum):
    UNFILLED = 'UNFILLED'
    FILLED = 'FILLED'
    PARTIAL = 'PARTIAL'


class OrderType(enum.Enum):
    BASE = 'ABSTRACT_BASE'
    LIMIT_ORDER = 'LIMIT_ORDER'
    MARKET_ORDER = 'MARKET_ORDER'
    TAKE_PROFIT_ORDER = 'TAKE_PROFIT_ORDER'
    STOP_LOSS_ORDER = 'STOP_LOSS_ORDER'
    BRACKET_ORDER = 'BRACKET_ORDER'


class ChildOrderType(enum.Enum):
    TAKE_PROFIT = 'TAKE_PROFIT'
    STOP_LOSS = 'STOP_LOSS'
    UNKNOWN = 'UNKNOWN'


CHILD_TYPE_MAP = {
    1: ChildOrderType.TAKE_PROFIT,
    4: ChildOrderType.STOP_LOSS,
}

BASE_EQUALITY = [
    'creation_time', 'order_id', 'security_code', 'exchange_code', 'quantity', 'is_buy', 'basket_id', 'in_market',
    'filled_quantity', 'fills', 'cancelled', 'cancelled_at', 'cancelled_id', 'cancelled_quantity', 'modified',
    'modify_count', 'modify_history', 'rejected', 'rejected_at', 'rejected_reason',
]


class BaseOrder(metaclass=abc.ABCMeta):
    """
    Base Order class, records and updates order as exchange messages arrive
    """
    type = OrderType.BASE
    can_modify = False
    can_cancel = True
    modify_field = None
    _equality_checks = BASE_EQUALITY
    _extra_checks = []

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool):
        """
        Base Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        """
        self.creation_time = get_utc_now()
        self.order_id = order_id
        self.security_code = security_code
        self.exchange_code = exchange_code
        self.quantity = quantity
        self.is_buy = is_buy
        self.basket_id = None
        self.in_market = False
        self.in_market_at = None
        self.filled_quantity = 0
        self.fills = []
        self.cancelled = False
        self.cancelled_at = None
        self.cancelled_id = None
        self.cancelled_quantity = 0
        self.modified = False
        self.modify_count = 0
        self.modify_history = dict()
        self.rejected = False
        self.rejected_at = None
        self.rejected_reason = None

    def __eq__(self, other):
        keys = self._equality_checks + self._extra_checks
        for key in keys:
            try:
                val_a = getattr(self, key)
                val_b = getattr(other, key)
                assert val_a == val_b
            except AssertionError:
                return False
        return True

    @property
    def have_initial_order_response(self):
        return self.in_market is True or self.rejected is True

    def _add_basket_id(self, basket_id: str, timestamp: dt) -> None:
        """
        Added once received from the Exchange; means the order is live in the market and flagged as such

        :param basket_id: (str) Unique Basket ID from the Exchange
        :return:
        """
        self.basket_id = basket_id
        self.in_market = True
        self.in_market_at = timestamp

    def _add_fill(self, fill_data: dict) -> None:
        """
        Adds new fills that come back from the exchange to the order and updates the filled quantity of the order

        :param fill_data: (dict) fill information
        :return:
        """
        self.fills.append(fill_data)
        self.filled_quantity += fill_data['quantity']

    def _cancel_order(self, timestamp: dt, cancelled_id: str, cancelled_qty: int) -> None:
        """
        Marks the order as cancelled with metadata as received from the Exchange

        :param timestamp: (dt) time of cancellation
        :param cancelled_id: (str) unique id of the cancellation from the exchange
        :return: None
        """
        if self.can_cancel is False:
            raise UncancellableOrderException('Order Type of {0} Cannot be Cancelled'.format(self.type))
        self.cancelled = True
        self.cancelled_at = timestamp
        self.cancelled_id = cancelled_id
        self.cancelled_quantity = cancelled_qty

    def _mark_order_rejected(self, timestamp: dt, rejected_reason: str) -> None:
        """Mark Order Rejected from Rithmic"""
        self.rejected = True
        self.rejected_at = timestamp
        self.rejected_reason = rejected_reason

    @property
    def _get_modify_level_value(self) -> float:
        """
        Gets either the trigger price (stop loss order) or limit price (limit & take profit orders)
        :return:
        """
        return getattr(self, self.modify_field)

    def _set_new_modified_level(self, new_level: float) -> None:
        """
        Gets either the trigger price (stop loss order) or limit price (limit & take profit orders)

        :param new_level: (float) new trigger price or limit price order has been modified to
        :return:
        """
        setattr(self, self.modify_field, new_level)

    def _modify_order(self, timestamp: dt, modify_id: str, new_level: float) -> None:
        """
        As a modification message from the exchange arrives, marks the order as modified, records metadata and changes
        the trigger price or limit price

        :param timestamp: (dt) Time order was modified at the exchange
        :param modify_id: (str) Unique Modification ID from the exchange
        :param new_level: (float) Level order has been modified to
        :return: None
        """
        if self.can_modify is False:
            raise UnmodifiableOrderException('Order Type of {0} Cannot be Modified'.format(self.type))
        modify_count = self.modify_count + 1
        self.modify_count = modify_count
        row = {
            'timestamp': timestamp, 'modify_id': modify_id,
            'new_{0}'.format(self.modify_field): new_level,
            'old_{0}'.format(self.modify_field): self._get_modify_level_value
        }
        self.modify_history[modify_count] = row
        self._set_new_modified_level(new_level)
        self.modified = True

    def __repr__(self):
        buy_sell = 'BUY' if self.is_buy else 'SELL'
        avg_px, avg_qty = self.average_fill_price_qty
        value = '{0} -> {1} {2} LOT OF {3} | STATUS={4}'.format(
            self.type, buy_sell, self.quantity, self.security_code, self.fill_status.name,
        )
        if self.fill_status != FillStatus.UNFILLED:
            value = '{0} | {1} @ {2:.2f}'.format(value, avg_qty, avg_px)
        if self.cancelled:
            value = '{0} | Order Cancelled at {1}; Cancellation ID {2}'.format(
                value, self.cancelled_at, self.cancelled_id
            )
        if self.modified:
            value = '{0} | Order Has Been Modified {1} Times; Last Modification: {2}'.format(
                value, self.modify_count, self.last_modification
            )
        if self.rejected:
            value = '{0} | Order REJECTED -> Rejected at {1}, reason: {2}'.format(
                value, self.rejected_at, self.rejected_reason
            )
        return value

    @property
    def fill_status(self) -> Union[FillStatus, None]:
        """
        Get the fill status of the order, either Filled, Unfilled or Partial
        :return: (FillStatus)
        """
        if self.filled_quantity == self.quantity:
            return FillStatus.FILLED
        elif 0 < self.filled_quantity < self.quantity:
            return FillStatus.PARTIAL
        elif self.filled_quantity == 0:
            return FillStatus.UNFILLED

    @property
    def fill_dataframe(self) -> DataFrame:
        """
        Pandas DataFrame representation of all fills received for the order
        :return: (DataFrame) see below Columns and dtypes

        timestamp        datetime64[ns, UTC]
        order_id                      object
        security_code                 object
        exchange_code                 object
        is_buy                          bool
        quantity                       int64
        price                        float64
        fill_id                       object
        """
        return pd.DataFrame(self.fills)

    @property
    def has_fills(self) -> bool:
        """
        Boolean whether order has 1 or more fills
        :return: (bool) True is any fills
        """
        return len(self.fills) > 0

    @property
    def is_unfilled(self) -> bool:
        """Boolean whether order is unfilled or not"""
        return not self.has_fills

    @property
    def fully_filled(self) -> bool:
        """Boolean whether order is fully filled"""
        return self.filled_quantity == self.quantity

    @property
    def unfilled_quantity(self) -> int:
        """Remaining quantity to be filled"""
        return self.quantity - self.filled_quantity

    @property
    def average_fill_price_qty(self) -> Tuple[float, int]:
        """
        Returns the average fill price and the quantity filled
        If unfilled, returns NaN and 0
        :return: (tuple) tuple of average fill price and quantity filled
        """
        if self.has_fills is False:
            return np.nan, 0
        df = self.fill_dataframe
        df = df.assign(qty_px=df.quantity * df.price)
        g = df.groupby('order_id').agg(
            quantity=('quantity', 'sum'), is_buy=('is_buy', 'first'),
            timestamp=('timestamp', 'last'), qty_px=('qty_px', 'sum')
        )
        g = g.assign(avg_px=g.qty_px / g.quantity).reset_index(drop=False)
        row = g.iloc[0]
        return row.avg_px, row.quantity

    @property
    def last_modification(self) -> Union[dict, None]:
        """
        If the order has been modified at some point, returns the details of the last modification mode
        :return:
        """
        if self.modified:
            return self.modify_history[self.modify_count]

    @property
    def order_is_open(self):
        if not (self.rejected or self.cancelled):
            if self.fill_status != FillStatus.FILLED:
                return True
        return False


class MarketOrder(BaseOrder):
    """
    Market Order, Submitted to the exchange and filled at the current Bid/Ask for a Sell/Buy
    """
    type = OrderType.MARKET_ORDER
    can_cancel = False

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool):
        """
        Market Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        """
        BaseOrder.__init__(self, order_id, security_code, exchange_code, quantity, is_buy)



class LimitOrder(BaseOrder):
    """
    Limit Order, Submitted to the exchange and filled at limit or better price
    """
    type = OrderType.LIMIT_ORDER
    can_modify = True
    modify_field = 'limit_price'
    _extra_checks = ['limit_price']

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool,
                 limit_price: float):
        """
        Limit Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill at
        """
        BaseOrder.__init__(self, order_id, security_code, exchange_code, quantity, is_buy)
        self.limit_price = limit_price


class TakeProfitOrder(LimitOrder):
    """
    Take Profit Order, same as limit order but is a child or a parent Bracket Order
    """
    type = OrderType.TAKE_PROFIT_ORDER

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool,
                 limit_price: float, parent_order_id: str):
        """
        Take Profit Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill at
        :param parent_order_id: (str) Order ID of the Bracket Order Parent
        """
        LimitOrder.__init__(self, order_id, security_code, exchange_code, quantity, is_buy, limit_price)
        self.parent_order_id = parent_order_id


class StopLossOrder(BaseOrder):
    """
    Stop Loss Order, is a child of a Parent Bracket Order, when the market price touches the trigger price this order
    is converted to a Market Order to close the position immediately
    """
    type = OrderType.STOP_LOSS_ORDER
    can_modify = True
    modify_field = 'trigger_price'
    _extra_checks = ['trigger_price']

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool,
                 trigger_price: float, parent_order_id: str):
        """
        Stop Loss Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param trigger_price: (float) Trigger price which once touched in market, converts the order to a Market Order
        :param parent_order_id: (str) Order ID of the Bracket Order Parent
        """
        BaseOrder.__init__(self, order_id, security_code, exchange_code, quantity, is_buy)
        self.trigger_price = trigger_price
        self.parent_order_id = parent_order_id
        self.stop_triggered = False

    def mark_stop_as_triggered(self):
        self.stop_triggered = True


CHILD_ORDER_TYPES = Union[StopLossOrder, TakeProfitOrder]


class BracketOrder(LimitOrder):
    """
    Bracket Order, Submitted to the exchange and filled at limit or better price.
    Once a fill comes in, a take profit and stop loss order in the opposite direction are created and added as
    children to the order.
    For every fill, a new take profit & stop loss order will be created, so there is a one to many relationship
    """
    type = OrderType.BRACKET_ORDER
    can_modify = False
    _extra_checks = [
        'tick_multiplier', 'take_profit_ticks', 'stop_loss_ticks', 'take_profit_limit_price', 'stop_loss_trigger_price',
        'all_stops_modified', 'all_stops_modified_count', 'all_stops_modified_history', 'all_take_profit_modified',
        'all_take_profit_modified_count', 'all_take_profit_modified_history',
        'stop_loss_orders', 'take_profit_orders',
    ]

    def __init__(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool,
                 limit_price: float, take_profit_ticks: int, stop_loss_ticks: int, tick_multiplier: float):
        """
        Bracket Order init method

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill the parent at
        :param take_profit_ticks: (int) Number of ticks from limit price to set Take Profit Limit Price
        :param stop_loss_ticks: (int) Number of ticks from limit price to set Stop Loss Trigger Price
        :param tick_multiplier: (float) Tick multiplier as a float

        Note this is currently only configured for STATIC Take Profit and Stop Loss creation.
        Eg on ES, if you submit with a limit of 4001.00 and get filled at 4000.50 (2 ticks better),
        the take profit and stop loss ticks will be calculated from the limit of 4001.00, not 4000.50
        """
        LimitOrder.__init__(self, order_id, security_code, exchange_code, quantity, is_buy, limit_price)
        self.take_profit_ticks = take_profit_ticks
        self.stop_loss_ticks = stop_loss_ticks
        multiplier = -1 if self.is_buy else 1
        self.stop_loss_trigger_price = limit_price + (stop_loss_ticks * multiplier * tick_multiplier)
        self.take_profit_limit_price = limit_price - (take_profit_ticks * multiplier * tick_multiplier)
        self.take_profit_orders: List[TakeProfitOrder] = []
        self.stop_loss_orders: List[StopLossOrder] = []
        self.tick_multiplier = tick_multiplier

        self.all_stops_modified = False
        self.all_stops_modified_count = 0
        self.all_stops_modified_history = dict()

        self.all_take_profit_modified = False
        self.all_take_profit_modified_count = 0
        self.all_take_profit_modified_history = dict()

    def _add_take_profit_order(self, order: TakeProfitOrder) -> None:
        """
        Add a Take Profit Order child as notified by the exchange
        :param order: (TakeProfitOrder) auto created child order
        :return: None
        """
        self.take_profit_orders.append(order)

    def _add_stop_loss_order(self, order: StopLossOrder) -> None:
        """
        Add a Stop Loss Order child as notified by the exchange
        :param order: (StopLossOrder) auto created child order
        :return: None
        """
        self.stop_loss_orders.append(order)

    def _add_child_order(self, order: CHILD_ORDER_TYPES, child_order_type: ChildOrderType) -> None:
        """
        Route the new child to the correct bucket

        :param order: (StopLossOrder | TakeProfitOrder) order to route
        :param child_order_type: (ChildOrderType) type of child order
        :return:
        """
        if child_order_type == ChildOrderType.TAKE_PROFIT:
            self._add_take_profit_order(order)
        elif child_order_type == ChildOrderType.STOP_LOSS:
            self._add_stop_loss_order(order)

    @property
    def generate_new_take_profit_order_id(self) -> str:
        """
        Generates the next child order id for take profit orders

        :return: (str) unique order id
        """
        child_count = len(self.take_profit_orders)
        return '{0}_take_profit_{1}'.format(self.order_id, child_count)

    @property
    def generate_new_stop_loss_order_id(self) -> str:
        """
        Generates the next child order id for stop loss orders

        :return: (str) unique order id
        """
        child_count = len(self.stop_loss_orders)
        return '{0}_stop_loss_{1}'.format(self.order_id, child_count)

    @property
    def children_in_market(self) -> bool:
        """
        Does the bracket order have take profits and stops in the market

        :return: (bool)
        """
        return len(self.take_profit_orders) > 0 and len(self.stop_loss_orders) > 0

    @property
    def child_orders(self) -> tuple:
        """
        Convenience property to get all children in two buckets
        :return: (tuple) take profit orders and stop loss orders
        """
        return self.take_profit_orders, self.stop_loss_orders

    @property
    def all_child_orders(self) -> List[CHILD_ORDER_TYPES]:
        """
        Returns all child orders in a single list

        :return: (list) of all child orders
        """
        return self.take_profit_orders + self.stop_loss_orders

    @property
    def all_children_cancelled(self) -> bool:
        """
        Returns True if all child orders have been cancelled in the market

        :return: (bool)
        """
        return all(o.cancelled for o in self.all_child_orders)

    @property
    def all_stop_loss_orders_unfilled(self) -> bool:
        """
        Returns True if all stop loss orders are unfilled

        :return: (bool)
        """
        return all(o.fill_status == FillStatus.UNFILLED for o in self.stop_loss_orders)

    @property
    def all_take_profit_orders_unfilled(self) -> bool:
        """
        Returns True if all take profit orders are unfilled

        :return: (bool)
        """
        return all(o.fill_status == FillStatus.UNFILLED for o in self.take_profit_orders)

    @property
    def all_stop_loss_orders_filled(self) -> bool:
        """
        Returns True if all stop loss orders are filled

        :return: (bool)
        """
        return all(o.fill_status == FillStatus.FILLED for o in self.stop_loss_orders)

    @property
    def all_take_profit_orders_filled(self) -> bool:
        """
        Returns True if all take profit orders are filled

        :return: (bool)
        """
        return all(o.fill_status == FillStatus.FILLED for o in self.take_profit_orders)

    @property
    def all_stop_loss_orders_cancelled(self) -> bool:
        """
        Returns True if all stop loss orders are cancelled

        :return: (bool)
        """
        return all(o.cancelled for o in self.stop_loss_orders)

    @property
    def all_take_profit_orders_cancelled(self) -> bool:
        """
        Returns True if all take profit orders are cancelled

        :return: (bool)
        """
        return all(o.cancelled for o in self.take_profit_orders)

    @property
    def child_side_filled(self) -> Tuple[bool, Union[ChildOrderType, None]]:
        """
        Returns a tuple of boolean whether all of one child set is filled and which child type it is
        :return: (tuple) (bool, ChildOrderType)
        """
        stops_filled = self.all_stop_loss_orders_filled
        filled = stops_filled or self.all_take_profit_orders_filled
        child_type = None
        if filled:
            child_type = ChildOrderType.STOP_LOSS if stops_filled else ChildOrderType.TAKE_PROFIT
        return filled, child_type

    @property
    def filled_children_complete(self) -> bool:
        """
        Returns True if the parent is filled and one side of the children is fully filled too

        :return: (bool)
        """
        if self.fill_status == FillStatus.FILLED:
            child_filled, child_type = self.child_side_filled
            if child_filled:
                if child_type == ChildOrderType.STOP_LOSS and self.all_take_profit_orders_cancelled:
                    return True
                elif child_type == ChildOrderType.TAKE_PROFIT and self.all_stop_loss_orders_cancelled:
                    return True

    @property
    def stop_loss_filled_quantity(self):
        return sum([o.filled_quantity for o in self.stop_loss_orders])

    @property
    def take_profit_filled_quantity(self):
        return sum([o.filled_quantity for o in self.take_profit_orders])

    @property
    def child_filled_total(self):
        return self.stop_loss_filled_quantity + self.take_profit_filled_quantity

    @property
    def parent_and_child_fill_quantity_complete(self):
        if self.filled_quantity > 0:
            return self.filled_quantity == self.child_filled_total
        return False

    @property
    def order_is_open(self):
        if not (self.rejected or self.cancelled):
            if self.fill_status != FillStatus.FILLED:
                return True
            else:
                if self.filled_quantity != (self.stop_loss_filled_quantity + self.take_profit_filled_quantity):
                    return True
        return False

    def update_stop_loss_trigger_price(self, trigger_price: float):
        self.stop_loss_trigger_price = trigger_price

    def update_take_profit_limit_price(self, limit_price: float):
        self.take_profit_limit_price = limit_price


VALID_ORDER_TYPES = Union[MarketOrder, LimitOrder, BracketOrder, StopLossOrder, TakeProfitOrder]
