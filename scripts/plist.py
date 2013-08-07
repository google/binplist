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

import argparse
import logging
import json
import plistlib
import sys

from binplist import binplist


parser = argparse.ArgumentParser(description="A forensic plist parser.")
parser.add_argument(
  "plist", default=None, action="store",
  help="plist file to be parsed")
parser.add_argument(
  "-V", "--version", action="version", version=binplist.__version__)
parser.add_argument("-v", "--verbose", action="append_const", const=True,
                    help="Turn verbose logging on. Use twice for ultra "
                         "verbosity.")
parser.add_argument("-e", "--encoding", default="utf-8",
                    help="Sets the encoding of the output data.")


class BinplistJSONEncoder(json.JSONEncoder):
  def encode(self, o):
    if issubclass(o, binplist.NullValue):
      return "NULL"
    elif issubclass(o, binplist.CorruptReference):
      return "CORRUPTREF()"
    elif issubclass(o, binplist.RawValue):
      return "RAW(%s)" % o
    elif issubclass(o, binplist.UnknownObject):
      return "UNKNOWN()"


if __name__ == "__main__":
  options = parser.parse_args()
  if not options.plist:
    parser.print_help()
    sys.exit(-1)

  ultra_verbosity = False
  if options.verbose:
    if len(options.verbose) == 1:
      logging.basicConfig(level=logging.DEBUG)
    else:
      ultra_verbosity = True
      logging.basicConfig(level=binplist.LOG_ULTRA_VERBOSE)

  with open(options.plist) as fd:
    plist = binplist.BinaryPlist(file_obj=fd, ultra_verbosity=ultra_verbosity)
    try:
      parsed_plist = plist.Parse()
      if plist.is_corrupt:
        logging.warn("%s LOOKS CORRUPTED. You might not obtain all data!\n",
                     options.plist)
    except binplist.FormatError, e:
      parsed_plist = plistlib.readPlist(options.plist)
    print json.dumps(parsed_plist,
                     cls=BinplistJSONEncoder,
                     ensure_ascii=False,
                     indent=4).encode(options.encoding)