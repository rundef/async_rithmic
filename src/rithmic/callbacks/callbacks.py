import enum
from typing import Callable, Union

from rithmic.tools.pyrithmic_exceptions import CallbackIdNotFoundException


class CallbackId(enum.Enum):
    TICKER_LAST_TRADE = 150
    # Callback for Last Trade processed in TICKER plant, argument is a dictionary of live tick data
    TICKER_BEST_BID_OFFER = 151
    # Callback for Best Bid Offer processed in TICKER plant

    ORDER_RITHMIC_NOTIFICATIONS = 351
    # Callback to process notifications that stream from Rithmic in ORDER plant

    ORDER_EXCHANGE_NOTIFICATIONS = 352
    # Callback to process notifications that stream from the Exchange in ORDER plant

    ORDER_NEW_FILL_NOTIFICATION = 904
    # Callback processed by the Order API Status Manager when a new fill message is processed
    # Takes single argument of fill_data dictionary with the following keys:
    # dict_keys(
    # ['timestamp', 'order_id', 'parent_order_id', 'security_code', 'exchange_code', 'is_buy', 'quantity',
    # 'price', 'fill_id']
    # )

    HISTORY_DOWNLOAD_INTERMITTENT_PROCESSING = 902
    # Callback for Replay Tick Data as intermittent 10,000 rows of data are processed, can process this data
    # Takes two arguments, DataFrame of tick data and DownloadRequest object for all metadata

    HISTORY_DOWNLOAD_COMPLETE_PROCESSING = 903
    # Callback for Replay Tick Data once all records are returned
    # Takes two arguments, DataFrame of tick data and DownloadRequest object for all metadata




VALID_CALLBACK_IDS = [e.value for e in CallbackId]


class CallbackManager:
    """
    Callback Manager is used to register callbacks for different apis as updates flow from the exchange

    Eg Usage, callback for streaming tick data to process each row received:
        my_callback_fn = lambda row: print(row)
        cbm = CallbackManager()
        cbm.register_callback(CallbackId.TICKER_LAST_TRADE, my_callback_fn)

        api = RithmicTickerApi(callback_manager=cbm)
    """
    def __init__(self):
        """Init method sets mapping for callbacks"""
        self.callback_mapping = dict()

    def register_callback(self, callback_id: CallbackId, func: Callable) -> None:
        """
        Set a callback to be run on an async call in the interfaces

        :param callback_id: (CallbackId) valid callback id to attach func/method to
        :param func: (Callable) func/method to process callback
        :return: None
        """
        if callback_id.value not in VALID_CALLBACK_IDS:
            valid_str = ', '.join([str(i) for i in VALID_CALLBACK_IDS])
            raise CallbackIdNotFoundException(f'Callback ID {callback_id} is not found, valid ids: {valid_str}')
        self.callback_mapping[callback_id] = func

    def register_callbacks(self, callback_mapping: dict) -> None:
        """
        Convenience method to map multiple callbacks, provide dict of ID to callback func/method

        :param callback_mapping: (dict) of callbacks to set
        :return: None
        """
        for callback_id, fn in callback_mapping.items():
            self.register_callback(callback_id, fn)

    def get_callback_by_callback_id(self, callback_id: CallbackId) -> Union[Callable, None]:
        return self.callback_mapping.get(callback_id)

    def get_callback_by_template_id(self, template_id: int) -> Union[Callable, None]:
        try:
            callback_id = CallbackId(template_id)
        except ValueError as e:
            return
        return self.callback_mapping.get(callback_id)

    def callback_id_registered(self, callback_id: int) -> bool:
        return callback_id in self.callback_mapping

