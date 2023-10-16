# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: request_time_bar_replay.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='request_time_bar_replay.proto',
  package='rti',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=_b('\n\x1drequest_time_bar_replay.proto\x12\x03rti\"\xa4\x04\n\x14RequestTimeBarReplay\x12\x15\n\x0btemplate_id\x18\xe3\xb6\t \x02(\x05\x12\x12\n\x08user_msg\x18\x98\x8d\x08 \x03(\t\x12\x10\n\x06symbol\x18\x94\xdc\x06 \x01(\t\x12\x12\n\x08\x65xchange\x18\x95\xdc\x06 \x01(\t\x12\x35\n\x08\x62\x61r_type\x18\xa0\xa3\x07 \x01(\x0e\x32!.rti.RequestTimeBarReplay.BarType\x12\x19\n\x0f\x62\x61r_type_period\x18\xc8\xa2\x07 \x01(\x05\x12\x15\n\x0bstart_index\x18\xaa\xab\t \x01(\x05\x12\x16\n\x0c\x66inish_index\x18\xab\xab\t \x01(\x05\x12\x18\n\x0euser_max_count\x18\xa4\xb3\t \x01(\x05\x12\x38\n\tdirection\x18\x85\x8e\t \x01(\x0e\x32#.rti.RequestTimeBarReplay.Direction\x12\x39\n\ntime_order\x18\xbb\x8e\t \x01(\x0e\x32#.rti.RequestTimeBarReplay.TimeOrder\x12\x15\n\x0bresume_bars\x18\xaa\xb0\t \x01(\x08\"H\n\x07\x42\x61rType\x12\x0e\n\nSECOND_BAR\x10\x01\x12\x0e\n\nMINUTE_BAR\x10\x02\x12\r\n\tDAILY_BAR\x10\x03\x12\x0e\n\nWEEKLY_BAR\x10\x04\" \n\tDirection\x12\t\n\x05\x46IRST\x10\x01\x12\x08\n\x04LAST\x10\x02\"(\n\tTimeOrder\x12\x0c\n\x08\x46ORWARDS\x10\x01\x12\r\n\tBACKWARDS\x10\x02')
)



_REQUESTTIMEBARREPLAY_BARTYPE = _descriptor.EnumDescriptor(
  name='BarType',
  full_name='rti.RequestTimeBarReplay.BarType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SECOND_BAR', index=0, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MINUTE_BAR', index=1, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DAILY_BAR', index=2, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='WEEKLY_BAR', index=3, number=4,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=439,
  serialized_end=511,
)
_sym_db.RegisterEnumDescriptor(_REQUESTTIMEBARREPLAY_BARTYPE)

_REQUESTTIMEBARREPLAY_DIRECTION = _descriptor.EnumDescriptor(
  name='Direction',
  full_name='rti.RequestTimeBarReplay.Direction',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='FIRST', index=0, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='LAST', index=1, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=513,
  serialized_end=545,
)
_sym_db.RegisterEnumDescriptor(_REQUESTTIMEBARREPLAY_DIRECTION)

_REQUESTTIMEBARREPLAY_TIMEORDER = _descriptor.EnumDescriptor(
  name='TimeOrder',
  full_name='rti.RequestTimeBarReplay.TimeOrder',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='FORWARDS', index=0, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BACKWARDS', index=1, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=547,
  serialized_end=587,
)
_sym_db.RegisterEnumDescriptor(_REQUESTTIMEBARREPLAY_TIMEORDER)


_REQUESTTIMEBARREPLAY = _descriptor.Descriptor(
  name='RequestTimeBarReplay',
  full_name='rti.RequestTimeBarReplay',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='template_id', full_name='rti.RequestTimeBarReplay.template_id', index=0,
      number=154467, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='user_msg', full_name='rti.RequestTimeBarReplay.user_msg', index=1,
      number=132760, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='symbol', full_name='rti.RequestTimeBarReplay.symbol', index=2,
      number=110100, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='exchange', full_name='rti.RequestTimeBarReplay.exchange', index=3,
      number=110101, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='bar_type', full_name='rti.RequestTimeBarReplay.bar_type', index=4,
      number=119200, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='bar_type_period', full_name='rti.RequestTimeBarReplay.bar_type_period', index=5,
      number=119112, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='start_index', full_name='rti.RequestTimeBarReplay.start_index', index=6,
      number=153002, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='finish_index', full_name='rti.RequestTimeBarReplay.finish_index', index=7,
      number=153003, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='user_max_count', full_name='rti.RequestTimeBarReplay.user_max_count', index=8,
      number=154020, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='direction', full_name='rti.RequestTimeBarReplay.direction', index=9,
      number=149253, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='time_order', full_name='rti.RequestTimeBarReplay.time_order', index=10,
      number=149307, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='resume_bars', full_name='rti.RequestTimeBarReplay.resume_bars', index=11,
      number=153642, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _REQUESTTIMEBARREPLAY_BARTYPE,
    _REQUESTTIMEBARREPLAY_DIRECTION,
    _REQUESTTIMEBARREPLAY_TIMEORDER,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=39,
  serialized_end=587,
)

_REQUESTTIMEBARREPLAY.fields_by_name['bar_type'].enum_type = _REQUESTTIMEBARREPLAY_BARTYPE
_REQUESTTIMEBARREPLAY.fields_by_name['direction'].enum_type = _REQUESTTIMEBARREPLAY_DIRECTION
_REQUESTTIMEBARREPLAY.fields_by_name['time_order'].enum_type = _REQUESTTIMEBARREPLAY_TIMEORDER
_REQUESTTIMEBARREPLAY_BARTYPE.containing_type = _REQUESTTIMEBARREPLAY
_REQUESTTIMEBARREPLAY_DIRECTION.containing_type = _REQUESTTIMEBARREPLAY
_REQUESTTIMEBARREPLAY_TIMEORDER.containing_type = _REQUESTTIMEBARREPLAY
DESCRIPTOR.message_types_by_name['RequestTimeBarReplay'] = _REQUESTTIMEBARREPLAY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

RequestTimeBarReplay = _reflection.GeneratedProtocolMessageType('RequestTimeBarReplay', (_message.Message,), dict(
  DESCRIPTOR = _REQUESTTIMEBARREPLAY,
  __module__ = 'request_time_bar_replay_pb2'
  # @@protoc_insertion_point(class_scope:rti.RequestTimeBarReplay)
  ))
_sym_db.RegisterMessage(RequestTimeBarReplay)


# @@protoc_insertion_point(module_scope)