# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Flatbuffer support for communication with TDM.
"""

import re

class Table:

    def __init__(self, fields=None, default_values=None):
        # array of (value, encoded_value, is_inline)
        self.fields = fields or []
        self.default_values = default_values

    def __repr__(self):
        return f"Table({[f[0] if f is not None else None for f in self.fields]})"

    def add_field(self, value):
        self.fields.append(FlatBuffer.encode_value(value))

    @staticmethod
    def create_with_schema(fields, schema):
        if schema[0] != "T":
            raise Exception("unexpected schema for table")
        if type(fields) is Table:
            # already a table
            return fields

        # create table
        table = Table()
        ix_schema = 2
        for field in fields:
            field_data = FlatBuffer.convert_with_schema(field, schema[ix_schema:])
            table.fields.append(field_data)
            ix_schema += FlatBuffer.schema_item_length(schema, ix_schema)

        return table

    def encode(self):
        data = b""
        values = b""
        vtable = b""
        offsets = set()

        # encode all fields
        for i, field in enumerate(self.fields):
            if self.default_values is not None and field[0] == self.default_values[i]:
                vtable += FlatBuffer.encode_16(0)
            else:
                _, encoded_field, is_inline = field
                if encoded_field is None:
                    # no value (default)
                    vtable += FlatBuffer.encode_16(0)
                else:
                    vtable += FlatBuffer.encode_16(4 + len(data))
                    if is_inline:
                        data += encoded_field
                    else:
                        offsets.add((len(data), len(values)))
                        data += b"1234" # offset placeholder
                        values += encoded_field

        # prepend vtable header
        vtable = (FlatBuffer.encode_16(len(vtable) + 4)
                  + FlatBuffer.encode_16(4 + len(data))
                  + vtable)

        # append padding to vtable to align on 32-bit words
        if len(vtable) % 4 == 2:
            vtable += bytes([0, 0])

        # resolve offsets
        for offset_pos, offset_val in offsets:
            # adjust offset to be from here to encoded field
            offset_val += len(data) - offset_pos
            if offset_val % 4 == 2:
                raise Exception("internal (misaligned)")
            # insert it in table
            data = (data[:offset_pos]
                    + FlatBuffer.encode_32(offset_val)
                    + data[offset_pos+4:])

        # prepend vtable negated offset to table
        # (vtable follows field values)
        vtable_pos_offset = 4 + len(data) + len(values)
        data = FlatBuffer.encode_32(-vtable_pos_offset) + data

        return self, data + values + vtable, False

class Union(Table):

    def __init__(self, union_type, union_data):
        union_type_enc = (union_type, bytes([union_type, 0, 0, 0]), True)
        super(Union, self).__init__(fields=[union_type_enc, union_data])
        self.union_type = union_type
        self.union_data = union_data

    def __repr__(self):
        return f"Union(type={self.union_type},data={self.union_data})"

    @staticmethod
    def create_with_schema(fields, schema):
        if schema[0] != "U":
            raise Exception("unexpected schema for union")
        if type(fields) is Union:
            # already a union
            return fields

        union_type, union_value = fields

        # pick schema corresponding to union value
        ix_schema = 2
        for i in range(union_type - 1):
            ix_schema += FlatBuffer.schema_item_length(schema, ix_schema)

        # create union
        union_data = FlatBuffer.convert_with_schema(union_value, schema[ix_schema:])
        union = Union(union_type, union_data)
        return union


class FlatBuffer:

    def __init__(self):
        self.root = Table()

    def reset(self):
        self.root = Table()

    def add_field(self, value):
        self.root.add_field(value)

    def encode(self):
        encoded_root_table = self.root[1]
        return FlatBuffer.encode_32(4) + encoded_root_table

    @staticmethod
    def field_val(f, default):
        return f[0] if f is not None else default

    @staticmethod
    def normalize_schema(schema):
        # discard blanks and c++ comments
        re_comment = re.compile(r"//.*$")
        return ("".join([re_comment.sub("", line) for line in schema.split("\n")])
                  .replace(" ", "")
                  .replace("\t", ""))

    def parse(self, encoded_fb, schema):
        """Decode an encoded flatbuffer and populate self.
        Parameter schema is a string which describes what's expected:
        i=int32, u=uint8, b=bool, 2=short, s=string, *...=vector, S(...)=struct, T(...)=table, U(...)=union
        blanks and c++ comments are ignored
        """

        schema = FlatBuffer.normalize_schema(schema)

        if schema[0] not in "TU":
            raise Exception("unexpected schema")
        self.root = FlatBuffer.parse_value(encoded_fb, 0, schema)

    @staticmethod
    def schema_item_length(schema, index=0):
        """Find length of schema element at specified index.
        """
        if schema[index] in "ibusl2dx.":
            return 1
        if schema[index] in "STU":
            if schema[index + 1] != "(":
                raise Exception("schema syntax error")
            i = 2
            while schema[index + i] != ")":
                i += FlatBuffer.schema_item_length(schema, index + i)
            return i + 1
        if schema[index] == "*":
            return 1 + FlatBuffer.schema_item_length(schema, index + 1)
        raise Exception(f"unexpected schema {schema[index]}")

    @staticmethod
    def schema_item_data_size(schema, index=0):
        """Find data size of item described by schema element at specified index.
        """
        if schema[index] in "i*TU":
            return 4
        elif schema[index] in "bus.":
            return 1
        elif schema[index] in "ld":
            return 8
        else:
            raise Exception(f"unknown data size for schema {schema[index]}")

    @staticmethod
    def is_data_inline(schema, index=0):
        return schema[index] in "i2ubld"

    @staticmethod
    def parse_value(encoded_fb, pos, schema):
        if schema[0] == "i":
            return FlatBuffer.decode_i32(encoded_fb, pos)
        elif schema[0] == 'l':
            return FlatBuffer.decode_i64(encoded_fb, pos)
        elif schema[0] == "2":
            return FlatBuffer.decode_i16(encoded_fb, pos)
        elif schema[0] == "u":
            return encoded_fb[pos : pos + 1]
        elif schema[0] == "b":
            return encoded_fb[pos] != 0
        elif schema[0] == "s":
            str_pos = pos + FlatBuffer.decode_i32(encoded_fb, pos)
            str_len = FlatBuffer.decode_u32(encoded_fb, str_pos)
            return str(encoded_fb[str_pos + 4 : str_pos + 4 + str_len], "utf-8")
        elif schema[0] == "*":
            # decode vector
            vec_pos = pos + FlatBuffer.decode_i32(encoded_fb, pos)
            vec_len = FlatBuffer.decode_u32(encoded_fb, vec_pos)
            el_size = FlatBuffer.schema_item_data_size(schema, 1)
            if schema[1] == "u" and el_size == 1:
                # special case for bytes: decode as byte array
                return encoded_fb[vec_pos + 4 : vec_pos + 4 + vec_len]
            else:
                els = []
                for i in range(vec_len):
                    # decode element
                    els.append(FlatBuffer.parse_value(encoded_fb,
                                                      vec_pos + 4 + i * el_size,
                                                      schema[1:]))
                return els
        elif schema[0] == "T":
            # decode vtable
            if schema[1] != "(":
                raise Exception("schema syntax error")
            table_pos = pos + FlatBuffer.decode_u32(encoded_fb, pos)
            vtable_pos = table_pos - FlatBuffer.decode_i32(encoded_fb, table_pos)
            vtable_len = FlatBuffer.decode_u16(encoded_fb, vtable_pos)
            table_len = FlatBuffer.decode_u16(encoded_fb, vtable_pos + 2)
            vtable = [
                FlatBuffer.decode_u16(encoded_fb, vtable_pos + 4 + 2 * i)
                for i in range(vtable_len // 2 - 2)
            ]
            # decode table fields according to schema
            ix_schema = 2
            fields = []
            while schema[ix_schema] != ")":
                if len(fields) >= len(vtable) or vtable[len(fields)] == 0:
                    # missing value: None (stands for default value)
                    fields.append(None)
                else:
                    # decode field
                    pos_field = table_pos + vtable[len(fields)]
                    field_value = FlatBuffer.parse_value(encoded_fb,
                                                         pos_field,
                                                         schema[ix_schema:])
                    fields.append((field_value, None, FlatBuffer.is_data_inline(schema[ix_schema:])))
                ix_schema += FlatBuffer.schema_item_length(schema, ix_schema)
            return Table(fields=fields)
        elif schema[0] == "U":
            # uint8 _type, content
            # decode vtable
            if schema[1] != "(":
                raise Exception("schema syntax error")
            table_pos = pos + FlatBuffer.decode_u32(encoded_fb, pos)
            vtable_pos = table_pos - FlatBuffer.decode_i32(encoded_fb, table_pos)
            vtable_len = FlatBuffer.decode_u16(encoded_fb, vtable_pos)
            table_len = FlatBuffer.decode_u16(encoded_fb, vtable_pos + 2)
            vtable = [
                FlatBuffer.decode_u16(encoded_fb, vtable_pos + 4 + 2 * i)
                for i in range(vtable_len // 2 - 2)
            ]
            # get _type
            union_type = (FlatBuffer.parse_value(encoded_fb,
                                                 table_pos + vtable[0],
                                                 "u")[0]
                          if len(vtable) > 0 and vtable[0]
                          else 0)
            union_data = None
            # pick corresponding type in the union
            if union_type > 0:
                ix_schema = 2
                for i in range(union_type - 1):
                    if schema[ix_schema] == ")":
                        raise Exception(f"_type={union_type} too large for schema")
                    ix_schema += FlatBuffer.schema_item_length(schema, ix_schema)
            # decode union field
            if len(vtable) > 1:
                pos_field = table_pos + vtable[1]
                union_value = FlatBuffer.parse_value(encoded_fb,
                                                     pos_field,
                                                     schema[ix_schema:])
                union_data = (union_value, None, FlatBuffer.is_data_inline(schema[ix_schema:]))
            return Union(union_type, union_data)
        elif schema[0] == "x":
            # flexbuffer
            vec_pos = pos + FlatBuffer.decode_i32(encoded_fb, pos)
            vec_len = FlatBuffer.decode_u32(encoded_fb, vec_pos)
            buf = encoded_fb[vec_pos + 4 : vec_pos + 4 + vec_len]
            return FlexBuffer.parse(buf)
        elif schema[0] == ".":
            # don't parse
            return None
        else:
            raise Exception(f"unknown schema char {schema[0]}")

    @staticmethod
    def convert_from_native_type(value):
        """Convert native, compact format to FlatBuffer. The following type
        mappings are performed: tuple to Table
        """

        if type(value) is tuple:
            fields = [
                FlatBuffer.convert_from_native_type(el)
                for el in value
            ]
            return Table(fields)
        else:
            return value

    def load_from_native_type(self, value):
        self.root = FlatBuffer.convert_from_native_type(value)

    @staticmethod
    def convert_with_schema(value, schema):
        """Convert value with a schema (required for "2", "U", etc.).
        """
        if schema[0] == "i":
            return value, FlatBuffer.encode_32(value), True
        elif schema[0] == "l":
            return value, FlatBuffer.encode_64(value), True
        elif schema[0] == "2":
            return value, FlatBuffer.encode_16(value) + bytes([0, 0]), True
        elif schema[0] == "u":
            return value, bytes([value & 0xff, 0, 0, 0]), True
        elif schema[0] == "b":
            return value, bytes([1 if value else 0, 0, 0, 0]), True
        elif schema[0] == "s":
            str_utf8 = bytes(value, "utf-8")
            enc = FlatBuffer.encode_32(len(str_utf8)) + str_utf8
            # append 1 to 4 nul bytes
            enc += bytes([0 for i in range(4 - len(enc) % 4)])
            return value, enc, False
        elif schema[0] == "*":
            enc = FlatBuffer.encode_32(len(value))
            if schema[1] == "u":
                if type(value) is bytes:
                    enc += value
                else:
                    enc += bytes(value)
            else:
                vector_data = b""
                for i, el in enumerate(value):
                    _, el_enc, el_inline = FlatBuffer.convert_with_schema(el, schema[1:])
                    if el_inline:
                        enc += el_enc
                    else:
                        el_offset = len(vector_data) + 4 * (len(value) - i)
                        enc += FlatBuffer.encode_32(el_offset)
                        vector_data += el_enc
                enc += vector_data
            # append 0 to 3 nul bytes
            enc += bytes([0 for i in range((4 - len(enc)) % 4)])
            return value, enc, False
        elif schema[0] == "T":
            if value is None:
                return value, None, False
            table = Table.create_with_schema(value, schema)
            return table.encode()
        elif schema[0] == "U":
            union = Union.create_with_schema(value, schema)
            return union.encode()
        elif schema[0] == "x":
            enc = FlexBuffer.encode_vec_untyped_int16(value)
            # prepend size
            enc = FlatBuffer.encode_32(len(enc)) + enc
            # append 0 to 3 nul bytes
            enc += bytes([0 for i in range((4 - len(enc)) % 4)])
            return value, enc, False
        else:
            raise Exception("unknown schema char {schema[0]}")

    def load_with_schema(self, value, schema):
        schema = FlatBuffer.normalize_schema(schema)
        self.root = FlatBuffer.convert_with_schema(value, schema)

    @staticmethod
    def decode_u16(b, pos):
        return b[pos] | (b[pos + 1] << 8)

    @staticmethod
    def decode_i16(b, pos):
        u16 = FlatBuffer.decode_u16(b, pos)
        return u16 - 0x10000 if u16 & 0x8000 else u16

    @staticmethod
    def decode_u32(b, pos):
        return (b[pos] | (b[pos + 1] << 8)
                | (b[pos + 2] << 16) | (b[pos + 3] << 24))

    @staticmethod
    def decode_i32(b, pos):
        u32 = FlatBuffer.decode_u32(b, pos)
        return u32 - 0x100000000 if u32 & 0x80000000 else u32

    @staticmethod
    def decode_u64(b, pos):
        return (b[pos] | (b[pos + 1] << 8)
                | (b[pos + 2] << 16) | (b[pos + 3] << 24)
                | (b[pos + 4] << 32) | (b[pos + 5] << 40)
                | (b[pos + 6] << 48) | (b[pos + 7] << 56))

    @staticmethod
    def decode_i64(b, pos):
        u64 = FlatBuffer.decode_u64(b, pos)
        return u64 - 0x10000000000000000 if u64 & 0x8000000000000000 else u64

    @staticmethod
    def encode_16(w16):
        """Encode a 16-bit word.
        """
        return bytes([w16 & 0xff, w16 >> 8 & 0xff])

    @staticmethod
    def encode_32(w32):
        """Encode a 32-bit word.
        """
        return bytes([w32 >> 8 * i & 0xff for i in range(4)])

    @staticmethod
    def encode_64(w64):
        """Encode a 64-bit word.
        """
        return bytes([w64 >> 8 * i & 0xff for i in range(8)])

    @staticmethod
    def encode_value(value):
        """Encode any supported value to data to be placed either inline in a
        table or struct, or appended after with a reference offset. Pad to
        32-bit words. Return (value, data, is_inline).
        """
        if type(value) == int:
            return value, FlatBuffer.encode_32(value), True
        elif type(value) == bytes:
            return value, value + bytes([0, 0, 0]), True
        elif type(value) == bool:
            return value, bytes([1 if value else 0, 0, 0, 0]), True
        elif type(value) == str:
            str_utf8 = bytes(value, "utf-8")
            enc = FlatBuffer.encode_32(len(str_utf8)) + str_utf8
            # append 1 to 4 nul bytes
            enc += bytes([0 for i in range(4 - len(enc) % 4)])
            return value, enc, False
        elif type(value) is Table:
            return value.encode()
        else:
            raise TypeError("unsupported type in FlatBuffer")

    def dump(self):

        def dump_value(value):
            if type(value) == int:
                print("int", value)
            elif type(value) == bytes:
                print("byte", value[0])
            elif type(value) == bool:
                print("bool", value)
            elif type(value) == str:
                print("str", value)
            elif type(value) == list:
                print(f"vector len={len(value)} [")
                for val in value:
                    dump_value(val)
                print("]")
            elif type(value) is Table:
                if len(value.fields) == 0:
                    print(f"table len=0")
                else:
                    print(f"table len={len(value.fields)} [")
                    for field in value.fields:
                        dump_value("None" if field is None else field[1])
                    print("]")
            elif type(value) is Union:
                print(f"union type={value.union_type} [")
                dump_value(value.union_data[1])
                print("]")
            elif value is None:
                print("none")
            else:
                print("unknown", value)

        dump_value(self.root)


class FlexBuffer:

    # https://google.github.io/flatbuffers/flatbuffers_internals.html
    # https://chromium.googlesource.com/external/github.com/google/flatbuffers/+/refs/tags/v1.6.0/include/flatbuffers/flexbuffers.h

    # lower 2 bits: size in flexbuffer
    BIT_WIDTH_8 = 0
    BIT_WIDTH_16 = 1
    BIT_WIDTH_32 = 2
    BIT_WIDTH_64 = 3

    # upper 6 bits: actual type
    TYPE_NULL = 0
    TYPE_INT = 1
    TYPE_UINT = 2
    TYPE_FLOAT = 3
    TYPE_KEY = 4
    TYPE_STRING = 5
    TYPE_INDIRECT_INT = 6
    TYPE_INDIRECT_UINT = 7
    TYPE_INDIRECT_FLOAT = 8
    TYPE_MAP = 9
    TYPE_VECTOR = 10
    TYPE_VECTOR_INT = 11
    TYPE_VECTOR_UINT = 12
    TYPE_VECTOR_FLOAT = 13
    TYPE_VECTOR_KEY = 14
    TYPE_VECTOR_STRING = 15
    TYPE_BLOB = 25

    @staticmethod
    def parse(buf):
        """Convert flexbuffer.
        """

        def parse_int(el_byte_size, p, index, type):
            if type >> 2 not in [FlexBuffer.TYPE_INT, FlexBuffer.TYPE_UINT]:
                raise Exception("flex type not supported")
            signed = type >> 2 == FlexBuffer.TYPE_INT
            p += el_byte_size * index
            if el_byte_size == 1:
                val = buf[p]
                if signed and val & 0x80:
                    val -= 0x100
            elif el_byte_size == 2:
                val = buf[p] | (buf[p + 1] << 8)
                if signed and val & 0x8000:
                    val -= 0x10000
            elif el_byte_size == 4:
                val = buf[p] | (buf[p + 1] << 8) | (buf[p + 2] << 16) | (buf[p + 3] << 24)
                if signed and val & 0x80000000:
                    val -= 0x100000000
            else:
                val = (buf[p] | (buf[p + 1] << 8) | (buf[p + 2] << 16) | (buf[p + 3] << 24)
                        | (buf[p + 4] << 32) | (buf[p + 5] << 40) | (buf[p + 6] << 48) | (buf[p + 7] << 56))
                if signed and val & 0x8000000000000000:
                    val -= 0x10000000000000000
            return val

        def parse_array(el_byte_size, p):
            num_el = parse_int(el_byte_size, p, -1, FlexBuffer.TYPE_UINT << 2)
            type_array_offset = p + num_el * el_byte_size
            array = [
                parse_int(el_byte_size, p, i, buf[type_array_offset + i])
                for i in range(num_el)
            ]
            return array

        def parse_element(type, p):
            flex_size = type & 3
            el_byte_size = 2 ** flex_size
            actual_type = type >> 2
            if actual_type == FlexBuffer.TYPE_NULL:
                return None
            elif actual_type == FlexBuffer.TYPE_VECTOR:
                return parse_array(el_byte_size, p - buf[p])
            raise Exception("flex not impl")

        # last byte: root width in bytes
        root_width = buf[-1]
        # previous byte: root type
        root_type = buf[-2]

        root = parse_element(root_type, len(buf) - 2 - root_width)

        return root

    @staticmethod
    def encode_vec_int16(a):
        # straight encoding as TYPE_VECTOR_INT without any optimization attempt,
        # 16-bit offsets

        def enc16(n):
            return bytes([n & 0xff, (n >> 8) & 0xff])

        enc = enc16(len(a))
        for el in a:
            enc += enc16(el)
        # backward offset to array beginning (not size) in bytes
        enc += enc16(2 * len(a))
        # root trailer
        enc += bytes([
            # type
            (FlexBuffer.TYPE_VECTOR_INT << 2) | FlexBuffer.BIT_WIDTH_16,
            # root byte width (just the backward offset)
            2
        ])
        return enc

    @staticmethod
    def encode_vec_untyped_int16(a):
        # straight encoding as TYPE_VECTOR without much optimization attempt

        def enc8(n):
            return bytes([n & 0xff])

        def enc16(n):
            return bytes([n & 0xff, (n >> 8) & 0xff])

        # array length
        enc = enc16(len(a))
        # array elements
        for el in a:
            enc += enc16(el)
        # element types in uint8
        el_type = enc8((FlexBuffer.TYPE_INT << 2) | FlexBuffer.BIT_WIDTH_16)
        enc += len(a) * el_type
        # backward offset to array beginning (not size) in bytes
        backward_offset = 3 * len(a)
        backward_offset_size = 1 if backward_offset < 256 else 2
        if backward_offset_size == 2:
            # add padding if necessary to align int16
            if backward_offset & 1:
                enc += b"\0"
                backward_offset += 1
            enc += enc16(backward_offset)
        else:
            enc += enc8(backward_offset)
        # root trailer
        enc += bytes([
            # type
            (FlexBuffer.TYPE_VECTOR << 2) | FlexBuffer.BIT_WIDTH_16,
            # root byte width (just the backward offset)
            backward_offset_size
        ])
        return enc
