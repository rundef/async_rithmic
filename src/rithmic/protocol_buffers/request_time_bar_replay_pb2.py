# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: request_time_bar_replay.proto
# Protobuf Python Version: 4.25.4
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1drequest_time_bar_replay.proto\x12\x03rti\"\xf3\x04\n\x14RequestTimeBarReplay\x12\x15\n\x0btemplate_id\x18\xe3\xb6\t \x01(\x05\x12\x12\n\x08user_msg\x18\x98\x8d\x08 \x03(\t\x12\x10\n\x06symbol\x18\x94\xdc\x06 \x01(\t\x12\x12\n\x08\x65xchange\x18\x95\xdc\x06 \x01(\t\x12\x35\n\x08\x62\x61r_type\x18\xa0\xa3\x07 \x01(\x0e\x32!.rti.RequestTimeBarReplay.BarType\x12\x19\n\x0f\x62\x61r_type_period\x18\xc8\xa2\x07 \x01(\x05\x12\x15\n\x0bstart_index\x18\xaa\xab\t \x01(\x05\x12\x16\n\x0c\x66inish_index\x18\xab\xab\t \x01(\x05\x12\x18\n\x0euser_max_count\x18\xa4\xb3\t \x01(\x05\x12\x38\n\tdirection\x18\x85\x8e\t \x01(\x0e\x32#.rti.RequestTimeBarReplay.Direction\x12\x39\n\ntime_order\x18\xbb\x8e\t \x01(\x0e\x32#.rti.RequestTimeBarReplay.TimeOrder\x12\x15\n\x0bresume_bars\x18\xaa\xb0\t \x01(\x08\"a\n\x07\x42\x61rType\x12\x17\n\x13\x42\x41RTYPE_UNSPECIFIED\x10\x00\x12\x0e\n\nSECOND_BAR\x10\x01\x12\x0e\n\nMINUTE_BAR\x10\x02\x12\r\n\tDAILY_BAR\x10\x03\x12\x0e\n\nWEEKLY_BAR\x10\x04\";\n\tDirection\x12\x19\n\x15\x44IRECTION_UNSPECIFIED\x10\x00\x12\t\n\x05\x46IRST\x10\x01\x12\x08\n\x04LAST\x10\x02\"C\n\tTimeOrder\x12\x19\n\x15TIMEORDER_UNSPECIFIED\x10\x00\x12\x0c\n\x08\x46ORWARDS\x10\x01\x12\r\n\tBACKWARDS\x10\x02\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'request_time_bar_replay_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_REQUESTTIMEBARREPLAY']._serialized_start=39
  _globals['_REQUESTTIMEBARREPLAY']._serialized_end=666
  _globals['_REQUESTTIMEBARREPLAY_BARTYPE']._serialized_start=439
  _globals['_REQUESTTIMEBARREPLAY_BARTYPE']._serialized_end=536
  _globals['_REQUESTTIMEBARREPLAY_DIRECTION']._serialized_start=538
  _globals['_REQUESTTIMEBARREPLAY_DIRECTION']._serialized_end=597
  _globals['_REQUESTTIMEBARREPLAY_TIMEORDER']._serialized_start=599
  _globals['_REQUESTTIMEBARREPLAY_TIMEORDER']._serialized_end=666
# @@protoc_insertion_point(module_scope)
