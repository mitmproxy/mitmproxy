#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- Apache License, Version 2.0 ----- 
Filename: GlobalTokens.py
Copyright 2014, David P. Shaw

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''
class GlobalTokens:
    SWITCH_PAGE = 0x00
    END = 0x01
    ENTITY = 0x02
    STR_I = 0x03
    LITERAL = 0x04
    EXT_I_0 = 0x40
    EXT_I_1 = 0x41
    EXT_I_2 = 0x42
    PI = 0x43
    LITERAL_C = 0x44
    EXT_T_0 = 0x80
    EXT_T_1 = 0x81
    EXT_T_2 = 0x82
    STR_T = 0x83
    LITERAL_A = 0x84
    EXT_0 = 0xC0
    EXT_1 = 0xC1
    EXT_2 = 0xC2
    OPAQUE = 0xC3
    LITERAL_AC = 0xC4