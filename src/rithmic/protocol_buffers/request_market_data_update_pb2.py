# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: request_market_data_update.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='request_market_data_update.proto',
  package='rti',
  serialized_pb=_b('\n request_market_data_update.proto\x12\x03rti\"\xaf\x04\n\x17RequestMarketDataUpdate\x12\x15\n\x0btemplate_id\x18\xe3\xb6\t \x02(\x05\x12\x12\n\x08user_msg\x18\x98\x8d\x08 \x03(\t\x12\x10\n\x06symbol\x18\x94\xdc\x06 \x01(\t\x12\x12\n\x08\x65xchange\x18\x95\xdc\x06 \x01(\t\x12\x37\n\x07request\x18\xa0\x8d\x06 \x01(\x0e\x32$.rti.RequestMarketDataUpdate.Request\x12\x15\n\x0bupdate_bits\x18\xe3\xb4\t \x01(\r\"\xc7\x02\n\nUpdateBits\x12\x0e\n\nLAST_TRADE\x10\x01\x12\x07\n\x03\x42\x42O\x10\x02\x12\x0e\n\nORDER_BOOK\x10\x04\x12\x08\n\x04OPEN\x10\x08\x12\x15\n\x11OPENING_INDICATOR\x10\x10\x12\x0c\n\x08HIGH_LOW\x10 \x12\x14\n\x10HIGH_BID_LOW_ASK\x10@\x12\n\n\x05\x43LOSE\x10\x80\x01\x12\x16\n\x11\x43LOSING_INDICATOR\x10\x80\x02\x12\x0f\n\nSETTLEMENT\x10\x80\x04\x12\x10\n\x0bMARKET_MODE\x10\x80\x08\x12\x12\n\rOPEN_INTEREST\x10\x80\x10\x12\x10\n\x0bMARGIN_RATE\x10\x80 \x12\x15\n\x10HIGH_PRICE_LIMIT\x10\x80@\x12\x15\n\x0fLOW_PRICE_LIMIT\x10\x80\x80\x01\x12\x1a\n\x14PROJECTED_SETTLEMENT\x10\x80\x80\x02\x12\x14\n\x0e\x41\x44JUSTED_CLOSE\x10\x80\x80\x04\")\n\x07Request\x12\r\n\tSUBSCRIBE\x10\x01\x12\x0f\n\x0bUNSUBSCRIBE\x10\x02')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)



_REQUESTMARKETDATAUPDATE_UPDATEBITS = _descriptor.EnumDescriptor(
  name='UpdateBits',
  full_name='rti.RequestMarketDataUpdate.UpdateBits',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='LAST_TRADE', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BBO', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ORDER_BOOK', index=2, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OPEN', index=3, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OPENING_INDICATOR', index=4, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='HIGH_LOW', index=5, number=32,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='HIGH_BID_LOW_ASK', index=6, number=64,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CLOSE', index=7, number=128,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CLOSING_INDICATOR', index=8, number=256,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SETTLEMENT', index=9, number=512,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MARKET_MODE', index=10, number=1024,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OPEN_INTEREST', index=11, number=2048,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MARGIN_RATE', index=12, number=4096,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='HIGH_PRICE_LIMIT', index=13, number=8192,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='LOW_PRICE_LIMIT', index=14, number=16384,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PROJECTED_SETTLEMENT', index=15, number=32768,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ADJUSTED_CLOSE', index=16, number=65536,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=231,
  serialized_end=558,
)
_sym_db.RegisterEnumDescriptor(_REQUESTMARKETDATAUPDATE_UPDATEBITS)

_REQUESTMARKETDATAUPDATE_REQUEST = _descriptor.EnumDescriptor(
  name='Request',
  full_name='rti.RequestMarketDataUpdate.Request',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SUBSCRIBE', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UNSUBSCRIBE', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=560,
  serialized_end=601,
)
_sym_db.RegisterEnumDescriptor(_REQUESTMARKETDATAUPDATE_REQUEST)


_REQUESTMARKETDATAUPDATE = _descriptor.Descriptor(
  name='RequestMarketDataUpdate',
  full_name='rti.RequestMarketDataUpdate',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='template_id', full_name='rti.RequestMarketDataUpdate.template_id', index=0,
      number=154467, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='user_msg', full_name='rti.RequestMarketDataUpdate.user_msg', index=1,
      number=132760, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='symbol', full_name='rti.RequestMarketDataUpdate.symbol', index=2,
      number=110100, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='exchange', full_name='rti.RequestMarketDataUpdate.exchange', index=3,
      number=110101, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='request', full_name='rti.RequestMarketDataUpdate.request', index=4,
      number=100000, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_bits', full_name='rti.RequestMarketDataUpdate.update_bits', index=5,
      number=154211, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _REQUESTMARKETDATAUPDATE_UPDATEBITS,
    _REQUESTMARKETDATAUPDATE_REQUEST,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=42,
  serialized_end=601,
)

_REQUESTMARKETDATAUPDATE.fields_by_name['request'].enum_type = _REQUESTMARKETDATAUPDATE_REQUEST
_REQUESTMARKETDATAUPDATE_UPDATEBITS.containing_type = _REQUESTMARKETDATAUPDATE
_REQUESTMARKETDATAUPDATE_REQUEST.containing_type = _REQUESTMARKETDATAUPDATE
DESCRIPTOR.message_types_by_name['RequestMarketDataUpdate'] = _REQUESTMARKETDATAUPDATE

RequestMarketDataUpdate = _reflection.GeneratedProtocolMessageType('RequestMarketDataUpdate', (_message.Message,), dict(
  DESCRIPTOR = _REQUESTMARKETDATAUPDATE,
  __module__ = 'request_market_data_update_pb2'
  # @@protoc_insertion_point(class_scope:rti.RequestMarketDataUpdate)
  ))
_sym_db.RegisterMessage(RequestMarketDataUpdate)


# @@protoc_insertion_point(module_scope)