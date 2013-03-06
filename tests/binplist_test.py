#!/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for binplist."""

import datetime
import logging
import os
import random
import StringIO
import unittest

from binplist import binplist
import pytz


class BinplistTest(unittest.TestCase):
  def setUp(self):
    notrailer = ("bplist00")  # header
    self.notrailer = StringIO.StringIO(notrailer)

    # A bplist of size 32, which lacks a full trailer
    # A dumb parser will try to start parsing the trailer at the header
    shorttrailer = ("bplist\x00\x00"  # header
                    "\x00\x00\x00\x00\x00"  # unused
                    "\x00"  # sortversion
                    "\x00"  # offset int size
                    "\x00"  # object ref size
                    "\x00\x00\x00\x00\x00\x00\x00\x00"  # num objects
                    "\x00\x00\x00\x00\x00\x00\x00\x00"  # top object
                   )
    # This could be interpreted as
    # "bplis"  # unused
    # "t"  # sortversion
    # "\x00"  # offset int size
    # "\x00"  # object ref size
    # "\x00\x00\x00\x00\x00\x00\x00\x00" # num objects
    # "\x00\x00\x00\x00\x00\x00\x00\x00" # top object
    # "\x00\x00\x00\x00\x00\x00\x00\x00" # object table offset
    # Note that this is an invalid plist for OSX
    self.shorttrailer = StringIO.StringIO(shorttrailer)

    # The smallest possible non-overlapping bplist
    # This is still not a valid plist for OSX
    minimal = ("bplist00"  # header
               "\x00\x00\x00\x00\x00"  # unused
               "\x01"  # sortversion
               "\x00"  # offset int size
               "\x00"  # object ref size
               "\x00\x00\x00\x00\x00\x00\x00\x00"  # num objects
               "\x00\x00\x00\x00\x00\x00\x00\x00"  # top object
               "\x00\x00\x00\x00\x00\x00\x00\x00"  # offset to offtable
              )
    self.minimal = StringIO.StringIO(minimal)

    # bplist with a single element. This is the smallest possible plist
    # that"s accepted by OSX.
    single = ("bplist00"  # header
              "\x09"  # offset table, points to the next byte
              "\x09"  # True object
              "\x00\x00\x00\x00\x00"  # unused
              "\x01"  # sortversion
              "\x01"  # offset int size
              "\x00"  # object ref size
              "\x00\x00\x00\x00\x00\x00\x00\x01"  # num objects
              "\x00\x00\x00\x00\x00\x00\x00\x00"  # top object
              "\x00\x00\x00\x00\x00\x00\x00\x08"  # offset to offtable
             )
    self.single = StringIO.StringIO(single)

    # bplist with more offsets than objects (shouldn't be a problem)
    short = ("bplist00"  # header
             "\x09\x0a\x0b\x0c\x0d\x0e"  # offset table
             "\x09"  # True object
             "\x00\x00\x00\x00\x00"  # unused
             "\x01"  # sortversion
             "\x01"  # offset int size
             "\x00"  # object ref size
             "\x00\x00\x00\x00\x00\x00\x00\x03"  # num objects
             "\x00\x00\x00\x00\x00\x00\x00\x00"  # top object
             "\x00\x00\x00\x00\x00\x00\x00\x08"  # offset to offtable
            )
    self.short = StringIO.StringIO(short)

    # bplist with an offset table that starts past the file
    overflow = ("bplist00"  # header
                "\x09"  # offset table, points to the next byte
                "\x09"  # True object
                "\x00\x00\x00\x00\x00"  # unused
                "\x01"  # sortversion
                "\x01"  # offset int size
                "\x00"  # object ref size
                "\x00\x00\x00\x00\x00\x00\x00\x01"  # num objects
                "\x00\x00\x00\x00\x00\x00\x00\x00"  # top object
                "\x00\x00\x00\x00\x00\x00\xFF\xFF"  # offset to offtable (OF)
               )
    self.overflow = StringIO.StringIO(overflow)
    # The minimal valid XML plist.
    self.min_xml = StringIO.StringIO('<?xml version="1.0" encoding="UTF-8"?>'
                                     '<plist></plist>')

  def testReadHeader(self):
    blank_header = StringIO.StringIO("")
    plist = binplist.BinaryPlist(blank_header)
    self.assertRaises(binplist.FormatError, plist._ReadHeader)
    wrong_header = StringIO.StringIO("bla")
    plist = binplist.BinaryPlist(wrong_header)
    self.assertRaises(binplist.FormatError, plist._ReadHeader)
    unknown_version = StringIO.StringIO("bplist99")
    plist = binplist.BinaryPlist(unknown_version)
    plist._ReadHeader()
    self.assertEqual(plist.version, "99")
    usual_header = StringIO.StringIO("bplist00")
    plist = binplist.BinaryPlist(usual_header)
    plist._ReadHeader()
    self.assertEqual(plist.version, "00")

  def testReadTrailer(self):
    blank_trailer = StringIO.StringIO("")
    plist = binplist.BinaryPlist(blank_trailer)
    self.assertRaises(IOError, plist._ReadTrailer)
    plist = binplist.BinaryPlist(self.minimal)
    # We allow parsing the minimal plist, even though it's not valid
    plist._ReadTrailer()

  def testParseOfftable(self):
    plist = binplist.BinaryPlist(self.minimal)
    # Start by parsing a minimal offsets table
    plist._ReadTrailer()
    plist._ReadOffsetTable()
    self.assertListEqual([], plist.object_offsets)
    # single offset table
    plist = binplist.BinaryPlist(self.single)
    plist._ReadTrailer()
    plist._ReadOffsetTable()
    self.assertListEqual([0x09], plist.object_offsets)
    # Test the plist that doesn't have a full trailer
    plist = binplist.BinaryPlist(self.short)
    plist._ReadTrailer()
    plist._ReadOffsetTable()
    self.assertListEqual([9, 10, 11], plist.object_offsets)
    # Test the plist with an offset table that overflows the file
    plist = binplist.BinaryPlist(self.overflow)
    plist._ReadTrailer()
    self.assertRaises(binplist.FormatError, plist._ReadOffsetTable)

  def testReadPlist(self):
    blank_file = StringIO.StringIO("")
    self.assertRaises(binplist.FormatError, binplist.readPlist, blank_file)
    bplist15 = StringIO.StringIO("bplist15")
    self.assertRaises(binplist.FormatError, binplist.readPlist, bplist15)
    # Incomplete XML does not parse (expat error from plistlib is caught)
    xml_file = StringIO.StringIO("<xml")
    self.assertRaises(binplist.FormatError, binplist.readPlist, xml_file)
    # Check that a minimal XML plist does parse.
    # We're not testing full XML parsing per se as that's plistlib's tests job.
    binplist.readPlist(self.min_xml)

  def testCanParseBinplistAtOffset(self):
    for _ in range(5):
      self.single.seek(0, os.SEEK_SET)
      rand_int = random.randint(0, 2048)
      padding = "A" * rand_int
      padded_singleplist = padding + self.single.read()
      fd = StringIO.StringIO(padded_singleplist)
      fd.seek(rand_int, os.SEEK_SET)
      plist = binplist.BinaryPlist(fd)
      plist.Parse()

  def testReadPlistCanParseXMLPlistAtOffset(self):
    for _ in range(5):
      self.min_xml.seek(0, os.SEEK_SET)
      rand_int = random.randint(0, 2048)
      padding = "A" * rand_int
      padded_xml_plist = padding + self.min_xml.read()
      fd = StringIO.StringIO(padded_xml_plist)
      fd.seek(rand_int, os.SEEK_SET)
      binplist.readPlist(fd)

  #############################################################################
  ##### Object-specific tests

  def testParseBoolFill(self):
    # null
    data = StringIO.StringIO("\x00")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(binplist.NullValue, plist._ParseObject())
    # false
    data = StringIO.StringIO("\x08")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(False, plist._ParseObject())
    # true
    data = StringIO.StringIO("\x09")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(True, plist._ParseObject())
    # fill byte
    data = StringIO.StringIO("\x0F")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(None, plist._ParseObject())
    # unknown
    for i in "\x01\x02\x03\x04\x05\x06\x07\x0a\x0b\x0c\x0d\x0e":
      unk = StringIO.StringIO(i)
      plist = binplist.BinaryPlist(unk)
      self.assertEqual(binplist.UnknownObject, plist._ParseObject())

  def testParseInt(self):
    # 1 byte
    data = StringIO.StringIO("\x10\x00")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(0, plist._ParseObject())
    # 2 bytes
    data = StringIO.StringIO("\x11\x00\x01")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(1, plist._ParseObject())
    data = StringIO.StringIO("\x11\x01\x00")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(256, plist._ParseObject())
    # 4 bytes
    data = StringIO.StringIO("\x12\x00\x00\x00\x01")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(1, plist._ParseObject())
    # 8 bytes - should be unsigned
    data = StringIO.StringIO("\x13\x00\x00\x00\x00\x00\x00\x00\x01")
    plist = binplist.BinaryPlist(data)
    self.assertEqual(1, plist._ParseObject())
    # Now with version 00 - signed
    data = StringIO.StringIO("\x13\x00\x00\x00\x00\x00\x00\x00\x01")
    plist = binplist.BinaryPlist(data)
    plist.version = "00"
    self.assertEqual(1, plist._ParseObject())
    # 8 bytes - should be unsigned
    data = StringIO.StringIO("\x13\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE")
    plist = binplist.BinaryPlist(data)
    self.assertEqual((1<<64)-2, plist._ParseObject())
    # Now with version 00 - signed
    data = StringIO.StringIO("\x13\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE")
    plist = binplist.BinaryPlist(data)
    plist.version = "00"
    self.assertEqual(-2, plist._ParseObject())
    # 16 bytes - should be unsigned
    raw = "\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    data = StringIO.StringIO(raw)
    plist = binplist.BinaryPlist(data)
    self.assertEqual(1, plist._ParseObject())
    raw = "\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    data = StringIO.StringIO(raw)
    plist = binplist.BinaryPlist(data)
    plist.version = "00"
    self.assertEqual(1, plist._ParseObject())
    # 16 bytes - should be unsigned
    raw = "\x14\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE"
    data = StringIO.StringIO(raw)
    plist = binplist.BinaryPlist(data)
    self.assertEqual((1<<128)-2, plist._ParseObject())
    # Now with version 00 - signed
    raw = "\x14\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE"
    data = StringIO.StringIO(raw)
    plist = binplist.BinaryPlist(data)
    plist.version = "00"
    self.assertEqual(-2, plist._ParseObject())
    # Test incomplete data
    data = StringIO.StringIO("\x10")
    plist = binplist.BinaryPlist(data)
    int_object = plist._ParseObject()
    self.assertTrue(isinstance(int_object, binplist.RawValue))
    data = StringIO.StringIO("\x11\x12")
    plist = binplist.BinaryPlist(data)
    int_object = plist._ParseObject()
    self.assertTrue(isinstance(int_object, binplist.RawValue))
    # Test unknown size
    data = StringIO.StringIO("\x16\x00\x00")
    plist = binplist.BinaryPlist(data)
    int_object = plist._ParseObject()
    self.assertEqual(int_object, binplist.RawValue("\x00\x00"))

  def testParseReal(self):
    values = [
        (0, "\x22\x00\x00\x00\x00", 0.0, float),
        (0, "\x22\x3f\x80\x00\x00", 1.0, float),
        (0, "\x22\xc1\xfa\xb2\x2d", -31.336999893188477, float),
        (0, "\x23\x00\x00\x00\x00\x00\x00\x00\x00", 0.0, float),
        (0, "\x23\xc0\x3f\x56\x45\xa1\xca\xc0\x83", -31.337, float),
        # Wrong size
        (0, "\x21\xc0\x3f", "\xc0\x3f", binplist.RawValue)
    ]
    self.ObjectTest(values)

  def testParseDate(self):
    datetime_cls = datetime.datetime
    values = [
        (0, "\x33"+"\x00"*8,  # plist epoch
         datetime_cls(2001, 1, 1, 0, 0, 0, tzinfo=pytz.utc), datetime_cls),
        (0, "\x33\xc0\xac\x20\x00\x00\x00\x00\x00",  # -1 hour
         datetime_cls(2000, 12, 31, 23, 0, 0, tzinfo=pytz.utc), datetime_cls),
        (0, "\x33\x41\xb6\x92\x5e\x80\x00\x00\x00",  # +12 years
         datetime_cls(2013, 1, 1, 0, 0, 0, tzinfo=pytz.utc), datetime_cls),
        # Now try microseconds
        (0, "\x33\x41\xb6\x92\x5e\x80\x00\x20\x00",  # +12 years and 488 us
         datetime_cls(2013, 1, 1, 0, 0, 0, 488, tzinfo=pytz.utc), datetime_cls),
        # Negative date
        (0, "\x33\xc1\xb6\x92\x5e\x80\x00\x00\x00",  # -12 years
         datetime_cls(1989, 1, 1, 0, 0, 0, tzinfo=pytz.utc), datetime_cls),
        # Wrong size count, we allow these
        (0, "\x31\x41\xb6\x92\x5e\x80\x00\x00\x00",  # +12 years
         datetime_cls(2013, 1, 1, 0, 0, 0, tzinfo=pytz.utc), datetime_cls),
        # And not enough data
        (0, "\x31\x41\xb6",
         binplist.RawValue("\x41\xb6"), binplist.RawValue),
    ]
    self.ObjectTest(values)

  def ObjectTest(self, values):
    for test_value in values:
      raises, data, expected_result, result_type = test_value
      fd = StringIO.StringIO(data)
      plist = binplist.BinaryPlist(fd)
      if not raises:
        result = plist._ParseObject()
        logging.debug("Result was %r.", result)
        self.assertTrue(isinstance(result, result_type))
        self.assertEqual(result, expected_result)
      else:
        self.assertRaises(expected_result, plist._ParseObject)

  def testParseData(self):
    values = [
        # Length 0 string
        (0, "\x40\x99\x33", "", basestring),
        # Length 1 string
        (0, "\x41\x99\x33", "\x99", basestring),
        # Length 4 string
        (0, "\x44data", "data", basestring),
        # Length 4 via sized int string
        (0, "\x4F\x00\x04data", "data", basestring),
        # Length 256 via sized int string
        (0, "\x4F\x01\x01\x00"+"\x7f"*256, "\x7f"*256, basestring),
        # Wrong size
        (0, "\x48dat", "dat", basestring),
        (0, "\x4F\x00\x04dat", "dat", basestring),
    ]
    self.ObjectTest(values)

  def testParseString(self):
    values = [
        # Length 0 string
        (0, "\x50blabla", "", basestring),
        # Length 1 string
        (0, "\x51d", "d", basestring),
        # Length 4 string
        (0, "\x54data", "data", basestring),
        # Length 4 via sized int string
        (0, "\x5F\x00\x04data", "data", basestring),
        # Length 4 via sized int string and non-ASCII chars
        (0, "\x5F\x00\x04\x9f\x88\xd3\xe6", "\x9f\x88\xd3\xe6", basestring),
        # Length 18 (tests the 1 << size & 0xF bug at GetSizedIntFromFd)
        (0, "\x5F\x10\x12"+"A"*18, "A"*18, basestring),
        # Length 256 via sized int string
        (0, "\x5F\x01\x01\x00"+"A"*256, "A"*256, basestring),
        # Wrong size, we return what we can
        (0, "\x58dat", "dat", basestring),
        (0, "\x5F\x00\x04dat", "dat", basestring),
    ]
    self.ObjectTest(values)

  def testParseUtf16(self):
    values = [
        # Length 0 string
        (0, "\x60blabla", "", unicode),
        # Length 1 string
        (0, "\x61\x00d", u"d", unicode),
        # Length 4 string
        (0, "\x64\x00d\x00a\x00t\x00a", u"data", unicode),
        # Length 4 via sized int string
        (0, "\x6F\x00\x04\x00d\x00a\x00t\x00a", u"data", unicode),
        # Length 4 via sized int string and non-ASCII chars
        (0, "\x6F\x00\x04\x9f\x88\xd3\xe6", u"\u9f88\ud3e6", unicode),
        # Length 256 via sized int string
        (0, "\x6F\x01\x01\x00"+"\x00A"*256, u"A"*256, unicode),
        # Odd-sized string, will return a raw value
        (0, "\x62\x00a\x00", "\x00a\x00", binplist.RawValue),
        # Wrong size, we return what we can as RawValue.
        (0, "\x68dat", "dat", binplist.RawValue),
        (0, "\x6F\x00\x04dat", "dat", binplist.RawValue),
    ]
    self.ObjectTest(values)

  def testParseUid(self):
    # This is experimental as we haven't seen actual UID values yet.
    values = [
        # UID of length 1
        (0, "\x80\x01", 1, int),
        # UID of length 2
        (0, "\x81\x00\x01", 1, int),
        # UID of length 4
        (0, "\x83\x00\x00\x00\x01", 1, int),
        # UID of length 8
        (0, "\x87\x00\x00\x00\x00\x00\x00\x00\x01", 1, int),
        # UID of length 3 with enough data
        (0, "\x82\x00\x00\x00\x00\x00\x00\x00\x01", 0, int),
        # UID of length 3 without enough data. We return what we can
        (0, "\x82\x00\x01", 1, int),
    ]
    self.ObjectTest(values)

  def testParseArray(self):
    values = [
        # (ref_size, object_offsets, expected_result, data)
        # Array of 0 objects
        (1, [], [], "\xA0"),
        # Array of 1 object
        (1,
         [0, 2],
         [False],
         ("\xA1"  # Array of 1 object
          "\x01"  # Reference to object False
          "\x08"  # False object
         )),
        # Array of 2 objects
        (1,
         [0, 3, 4],
         [False, True],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to object False
          "\x02"  # Reference to object True
          "\x08"  # False object
          "\x09"  # True object
         )),
        # Array of 2 objects, 1 nonexistant
        (1,
         [0, 3, 4],
         [False, binplist.CorruptReference],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to object False
          "\x09"  # Reference to a nonexistant object
          "\x08"  # False object
          "\x09"  # True object
         )),
        # Array of 2 objects, 1 out of bounds
        (1,
         [0, 3, 200],
         [False, binplist.CorruptReference],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to object False
          "\x02"  # Reference out of bounds
          "\x08"  # False object
          "\x09"  # True object
         )),
        # Array of 2 objects, 1 circular reference to the array itself
        (1,
         [0, 3, 4],
         [False, binplist.CorruptReference],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to object False
          "\x00"  # circular reference to the array
          "\x08"  # False object
          "\x09"  # True object
         )),
        # Array of 2 objects, one a False value. The other is an array that
        # has a reference to the first array.
        # Tests deep circular reference detection
        (1,
         [0, 3, 4],
         [False, [binplist.CorruptReference]],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to object False
          "\x02"  # Reference to the second array
          "\x08"  # False object
          "\xA1"  # Array of 1 object, points to the first array
          "\x00"  # circular reference to the first array
         )),
        # Array with not enough elements. This is hardly possible
        # in a real world scenario because of the trailer always being
        # past the objects. However on a corrupt bplist the object offset might
        # be pointing to the last elements of the trailer, one of them
        # being interpreted as an array... Thus why this scenario.
        (1,
         [0, 3, 4],
         [binplist.CorruptReference, binplist.CorruptReference],
         ("\xA2"  # Array of 2 objects
          "\x01"  # Reference to a nonexistant object
         )),

        ]

    for value in values:
      (ref_size, object_offsets, expected_result, data) = value
      fd = StringIO.StringIO(data)
      plist = binplist.BinaryPlist(fd)
      # Fill objects_traversed with the current value as if we had been called
      # by a normal _Parse
      plist.objects_traversed = set([0])
      plist.object_ref_size = ref_size
      plist.object_offsets = object_offsets
      plist.object_count = len(object_offsets)
      result = plist._ParseObject()
      self.assertListEqual(expected_result, result)
      # Test that the circular reference detection helper is cleaned properly
      self.assertSetEqual(plist.objects_traversed, set([0]))

  def testParseDict(self):
    values = [
        # (ref_size, object_offsets, expected_result, data)
        # Dict of 0 objects
        (1, [], {}, "\xD0"),
        # Dict of 1 entry
        (1, [0, 3, 5],
         {"a": True},
         ("\xD1"  # Dict of 1 entry
          "\x01"  # Ref to key#1
          "\x02"  # Ref to val#1
          "\x51a"  # "a" (key#1)
          "\x09"  # True (val#1)
         )),
        # Dict of 1 entry, a key being an integer
        (1, [0, 3, 5],
         {1: True},
         ("\xD1"  # Dict of 1 entry
          "\x01"  # Ref to key#1
          "\x02"  # Ref to val#1
          "\x10\x01"  # 1 (key#1)
          "\x09"  # True (val#1)
         )),
        # Dict of 1 entry, has a circular key
        (1, [0, 3, 5],
         {"corrupt:0": True},
         ("\xD1"  # Dict of 1 entry
          "\x00"  # Circular key
          "\x02"  # Ref to val#1
          "\x10\x01"  # 1 (key#1)
          "\x09"  # True (val#1)
         )),
        # Dict of 1 entry, has a circular value
        (1, [0, 3, 5],
         {1: binplist.CorruptReference},
         ("\xD1"  # Dict of 1 entry
          "\x01"  # Ref to key#1
          "\x00"  # Circular value
          "\x10\x01"  # 1 (key#1)
          "\x09"  # True (val#1)
         )),
        # Dict of 1 entry, has both a circular key and a circular value
        (1, [0, 3, 5],
         {"corrupt:0": binplist.CorruptReference},
         ("\xD1"  # Dict of 1 entry
          "\x00"  # Circular key
          "\x00"  # Circular value
          "\x10\x01"  # 1 (key#1)
          "\x09"  # True (val#1)
         )),
        # Dict of 1 entry, value is a list that contains a circular value
        (1, [0, 3, 5, 8],
         {"a": [binplist.CorruptReference, 1]},
         ("\xD1"  # Dict of 1 entry
          "\x01"  # key#1
          "\x02"  # val#1
          "\x51a"  # "a" (key#1)
          "\xA2\x00\x03"  # Array with 2 elements. The dict and an integer
          "\x10\x01"  # 1
         )),
        # Dict of 2 entries
        (1,
         [0, 5, 7, 9, 10],
         {"a": False, "b": True},
         ("\xD2"  # Dict of 2 entries
          "\x01"  # key#1
          "\x02"  # key#2
          "\x03"  # val#2
          "\x04"  # val#2
          "\x51a"  # "a"
          "\x51b"  # "b"
          "\x08"  # False object
          "\x09"  # True object
         )),
        # Dict with not enough references
        (1, [0],
         {"corrupt:1": binplist.CorruptReference},
         ("\xD1"  # Dict of 1 entry
          "\x01"  # key#1
         )),
        # Dict with a nonexistant reference
        (1, [0],
         {"corrupt:32": binplist.CorruptReference},
         ("\xD1"  # Dict of 1 entry
          "\x20"  # key#1
          "\x99"  # val#1
         )),
    ]

    for value in values:
      (ref_size, object_offsets, expected_result, data) = value
      fd = StringIO.StringIO(data)
      plist = binplist.BinaryPlist(fd)
      # Fill objects_traversed with the current value as if we had been called
      # by a normal _Parse
      plist.objects_traversed = set([0])
      plist.object_ref_size = ref_size
      plist.object_offsets = object_offsets
      plist.object_count = len(object_offsets)
      result = plist._ParseObject()
      self.assertEqual(expected_result, result)
      # Test that the circular reference detection helper is cleaned properly
      self.assertSetEqual(plist.objects_traversed, set([0]))


if __name__ == "__main__":
  unittest.main()
