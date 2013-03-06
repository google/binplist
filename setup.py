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

from setuptools import setup

setup(name="binplist",
      version="0.1.0",
      description="A binary plist parser",
      author="Jordi Sanchez",
      author_email="binplist.feedback@gmail.com",
      url="http://code.google.com/p/binplist",
      license="Apache Software License",
      packages=["binplist"],
      test_suite = "tests",
      scripts=['scripts/binplist'],
      install_requires=["pytz"],
      )
