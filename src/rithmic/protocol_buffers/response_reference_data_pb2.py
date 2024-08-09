# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: response_reference_data.proto
# Protobuf Python Version: 4.25.4
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1dresponse_reference_data.proto\x12\x03rti\"\xc0\t\n\x15ResponseReferenceData\x12\x15\n\x0btemplate_id\x18\xe3\xb6\t \x01(\x05\x12\x12\n\x08user_msg\x18\x98\x8d\x08 \x03(\t\x12\x11\n\x07rp_code\x18\x9e\x8d\x08 \x03(\t\x12\x17\n\rpresence_bits\x18\x92\x8d\t \x01(\r\x12\x14\n\nclear_bits\x18\xcb\xb7\t \x01(\r\x12\x10\n\x06symbol\x18\x94\xdc\x06 \x01(\t\x12\x12\n\x08\x65xchange\x18\x95\xdc\x06 \x01(\t\x12\x19\n\x0f\x65xchange_symbol\x18\xa2\xdc\x06 \x01(\t\x12\x15\n\x0bsymbol_name\x18\xa3\x8d\x06 \x01(\t\x12\x18\n\x0etrading_symbol\x18\xa7\xcb\t \x01(\t\x12\x1a\n\x10trading_exchange\x18\xa8\xcb\t \x01(\t\x12\x16\n\x0cproduct_code\x18\x8d\x93\x06 \x01(\t\x12\x19\n\x0finstrument_type\x18\xa4\xdc\x06 \x01(\t\x12\x1b\n\x11underlying_symbol\x18\xa2\x95\x06 \x01(\t\x12\x19\n\x0f\x65xpiration_date\x18\xe3\x8d\x06 \x01(\t\x12\x12\n\x08\x63urrency\x18\x8e\xb6\t \x01(\t\x12\x1c\n\x12put_call_indicator\x18\x8d\x8e\x06 \x01(\t\x12\x18\n\x0etick_size_type\x18\xb7\xb4\t \x01(\t\x12\x1e\n\x14price_display_format\x18\x96\xb6\t \x01(\t\x12\x15\n\x0bis_tradable\x18\xdc\xb9\t \x01(\t\x12+\n!is_underlying_for_binary_contrats\x18\xc8\xba\t \x01(\t\x12\x16\n\x0cstrike_price\x18\xe2\x8d\x06 \x01(\x01\x12\x14\n\nftoq_price\x18\x90\xb6\t \x01(\x01\x12\x14\n\nqtof_price\x18\x91\xb6\t \x01(\x01\x12\x1b\n\x11min_qprice_change\x18\x92\xb6\t \x01(\x01\x12\x1b\n\x11min_fprice_change\x18\x93\xb6\t \x01(\x01\x12\x1c\n\x12single_point_value\x18\x95\xb6\t \x01(\x01\"\xf4\x03\n\x0cPresenceBits\x12\x1c\n\x18PRESENCEBITS_UNSPECIFIED\x10\x00\x12\x13\n\x0f\x45XCHANGE_SYMBOL\x10\x01\x12\x0f\n\x0bSYMBOL_NAME\x10\x02\x12\x10\n\x0cPRODUCT_CODE\x10\x04\x12\x13\n\x0fINSTRUMENT_TYPE\x10\x08\x12\x15\n\x11UNDERLYING_SYMBOL\x10\x10\x12\x13\n\x0f\x45XPIRATION_DATE\x10 \x12\x0c\n\x08\x43URRENCY\x10@\x12\x17\n\x12PUT_CALL_INDICATOR\x10\x80\x01\x12\x11\n\x0cSTRIKE_PRICE\x10\x80\x02\x12\x15\n\x10\x46PRICE_TO_QPRICE\x10\x80\x04\x12\x15\n\x10QPRICE_TO_FPRICE\x10\x80\x08\x12\x16\n\x11MIN_QPRICE_CHANGE\x10\x80\x10\x12\x16\n\x11MIN_FRPICE_CHANGE\x10\x80 \x12\x17\n\x12SINGLE_POINT_VALUE\x10\x80@\x12\x14\n\x0eTICK_SIZE_TYPE\x10\x80\x80\x01\x12\x1a\n\x14PRICE_DISPLAY_FORMAT\x10\x80\x80\x02\x12\x11\n\x0bIS_TRADABLE\x10\x80\x80\x04\x12\x14\n\x0eTRADING_SYMBOL\x10\x80\x80\x08\x12\x16\n\x10TRADING_EXCHANGE\x10\x80\x80\x10\x12)\n\"IS_UNDERLYING_FOR_BINARY_CONTRACTS\x10\x80\x80\x80\x04\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'response_reference_data_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_RESPONSEREFERENCEDATA']._serialized_start=39
  _globals['_RESPONSEREFERENCEDATA']._serialized_end=1255
  _globals['_RESPONSEREFERENCEDATA_PRESENCEBITS']._serialized_start=755
  _globals['_RESPONSEREFERENCEDATA_PRESENCEBITS']._serialized_end=1255
# @@protoc_insertion_point(module_scope)
