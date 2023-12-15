# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Extended XML parser that preserves the xmlns attributes
"""

import xml.etree.ElementTree as ET


class XMLParser(ET.XMLPullParser):
    '''
    Extended XML parser that add namespaces to ELements as
    xmlns/xmlns:... attributes
    '''
    def __init__(self: "XMLParser", source: str = None):
        '''
        Initialize the XML parser

        Args:
            source: optional string containing the whole XML document
        '''
        super().__init__(events=['start', 'start-ns', 'end-ns', 'end'])

        self._root = None
        self._namespaces = list()

        if source:
            self.feed(source)
            self.close()
            self.parse()

    def parse(self: "XMLParser"):
        '''Parse all events in current available data'''
        for ev_type, ev_data in self.read_events():
            if ev_type == 'start-ns':
                ns_name, ns_url = ev_data
                self._namespaces.append((ns_name, ns_url))
            elif ev_type == 'end-ns':
                ns_name = self._namespaces.pop()

            elif ev_type == 'start' and self._root is None:
                self._root = ev_data
            elif ev_type == 'end':
                for ns_name, ns_url in self._namespaces:
                    attr = 'xmlns' if ns_name == '' else 'xmlns:'+ns_name
                    ev_data.attrib[attr] = ns_url

    @property
    def root(self: "XMLParser"):
        '''Return root node

        Only valid if the first event has been parsed'''
        return self._root
