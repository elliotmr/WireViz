from dataclasses import dataclass, field
from typing import Any, List
from graphviz import Graph

COLOR_CODES = {'DIN': ['WH','BN','GN','YE','GY','PK','BU','RD','BK','VT'], # ,'GYPK','RDBU','WHGN','BNGN','WHYE','YEBN','WHGY','GYBN','WHPK','PKBN'],
               'IEC': ['BN','RD','OG','YE','GN','BU','VT','GY','WH','BK'],
               'BW':  ['BK','WH']}

# TODO: parse and render double-colored cables ('RDBU' etc)
color_hex = {
             'BK': '#000000',
             'WH': '#ffffff',
             'GY': '#999999',
             'PK': '#ff66cc',
             'RD': '#ff0000',
             'OG': '#ff8000',
             'YE': '#ffff00',
             'GN': '#009900',
             'TQ': '#00ffff',
             'BU': '#0066ff',
             'VT': '#8000ff',
             'BN': '#666600',
              }

color_full = {
             'BK': 'black',
             'WH': 'white',
             'GY': 'grey',
             'PK': 'pink',
             'RD': 'red',
             'OG': 'orange',
             'YE': 'yellow',
             'GN': 'green',
             'TQ': 'turquoise',
             'BU': 'blue',
             'VT': 'violet',
             'BN': 'brown',
}

color_ger = {
             'BK': 'sw',
             'WH': 'ws',
             'GY': 'gr',
             'PK': 'rs',
             'RD': 'rt',
             'OG': 'or',
             'YE': 'ge',
             'GN': 'gn',
             'TQ': 'tk',
             'BU': 'bl',
             'VT': 'vi',
             'BN': 'br',
}

class Harness:

    def __init__(self):
        self.color_mode = 'SHORT'
        self.nodes = {}
        self.cables = {}

    def add_node(self, name, *args, **kwargs):
        self.nodes[name] = Node(name, *args, **kwargs)

    def add_cable(self, name, *args, **kwargs):
        self.cables[name] = Cable(name, *args, **kwargs)

    def loop(self, node_name, from_pin, to_pin):
        self.nodes[node_name].loop(from_pin, to_pin)

    def connect(self, from_name, from_pin, via_name, via_pin, to_name, to_pin):
        self.cables[via_name].connect(from_name, from_pin, via_pin, to_name, to_pin)

    def connect_all_straight(self, cable_name, from_name, to_name):
        self.cables[cable_name].connect_all_straight(from_name, to_name)

    def create_graph(self):
        dot = Graph()
        dot.body.append('// Graph generated by WireViz')
        dot.body.append('// https://github.com/formatc1702/WireViz')
        font = 'arial'
        dot.attr('graph', rankdir='LR', ranksep='2', bgcolor='transparent', fontname=font)
        dot.attr('node', shape='record', style='rounded,filled', fillcolor='white', fontname=font)
        dot.attr('edge', style='bold', fontname=font)

        # prepare ports on connectors depending on which side they will connect
        for k, c in self.cables.items():
            for x in c.connections:
                if x[1] is not None: # connect to left
                    self.nodes[x[0]].ports_right = True
                if x[4] is not None: # connect to right
                    self.nodes[x[3]].ports_left = True

        for k, n in self.nodes.items():
            # a = attributes
            a = [n.type,
                 n.gender,
                 '{}-pin'.format(len(n.pinout)) if n.show_num_pins else '']
            # p = pinout
            p = [[],[],[]]
            p[1] = list(n.pinout)
            for i, x in enumerate(n.pinout, 1):
                if n.ports_left:
                    p[0].append('<p{portno}l>{portno}'.format(portno=i))
                if n.ports_right:
                    p[2].append('<p{portno}r>{portno}'.format(portno=i))
            # l = label
            l = [n.name if n.show_name else '', a, p]
            dot.node(k, label=nested(l))

            if len(n.loops) > 0:
                dot.attr('edge',color='#000000')
                if n.ports_left:
                    loop_side = 'l'
                    loop_dir = 'w'
                elif n.ports_right:
                    loop_side = 'r'
                    loop_dir = 'e'
                else:
                    raise Exception('No side for loops')
                for x in n.loops:
                    dot.edge('{name}:p{port_from}{loop_side}:{loop_dir}'.format(name=n.name, port_from=x[0], port_to=x[1], loop_side=loop_side, loop_dir=loop_dir),
                             '{name}:p{port_to}{loop_side}:{loop_dir}'.format(name=n.name, port_from=x[0], port_to=x[1], loop_side=loop_side, loop_dir=loop_dir))

        for k, c in self.cables.items():
            # a = attributes
            a = ['{}x'.format(len(c.colors)) if c.show_num_wires else '',
                 '{} mm\u00B2{}'.format(c.mm2, ' ({} AWG)'.format(awg_equiv(c.mm2)) if c.show_equiv else '') if c.mm2 is not None else '',
                 c.awg,
                 '+ S' if c.shield else '',
                 '{} m'.format(c.length) if c.length > 0 else '']
            # p = pinout
            p = [[],[],[]]
            for i, x in enumerate(c.colors,1):
                if c.show_pinout:
                    p[0].append('<w{wireno}i>{wireno}'.format(wireno=i))
                    p[1].append('{wirecolor}'.format(wirecolor=translate_color(x, self.color_mode)))
                    p[2].append('<w{wireno}o>{wireno}'.format(wireno=i))
                else:
                    p[1].append('<w{wireno}>{wirecolor}'.format(wireno=i,wirecolor=translate_color(x, self.color_mode)))
            if c.shield:
                if c.show_pinout:
                    p[0].append('<wsi>')
                    p[1].append('Shield')
                    p[2].append('<wso>')
                else:
                    p[1].append('<ws>Shield')
            # l = label
            l = [c.name if c.show_name else '', a, p]
            dot.node(k, label=nested(l))

            # connections
            for x in c.connections:
                if isinstance(x[2], int): # check if it's an actual wire and not a shield
                    search_color = c.colors[x[2]-1]
                    if search_color in color_hex:
                        dot.attr('edge',color='#000000:{wire_color}:#000000'.format(wire_color=color_hex[search_color]))
                    else: # color name not found
                        dot.attr('edge',color='#000000')
                else: # it's a shield connection
                    dot.attr('edge',color='#000000')
                if x[1] is not None: # connect to left
                    dot.edge('{from_name}:p{from_port}r'.format(from_name=x[0],from_port=x[1]),
                             '{via_name}:w{via_wire}{via_subport}'.format(via_name=c.name, via_wire=x[2], via_subport='i' if c.show_pinout else ''))
                    # self.nodes[x[0]].ports_right = True
                if x[4] is not None: # connect to right
                    dot.edge('{via_name}:w{via_wire}{via_subport}'.format(via_name=c.name, via_wire=x[2], via_subport='o' if c.show_pinout else ''),
                             '{to_name}:p{to_port}l'.format(to_name=x[3], to_port=x[4]))
                    # self.nodes[x[3]].ports_left = True

        return dot

    def output(self, filename, directory='_output', view=False, cleanup=True, format='pdf'):
        d = self.create_graph()
        for f in format:
            d.format = f
            d.render(filename=filename, directory=directory, view=view, cleanup=cleanup)
        d.save(filename='{}.gv'.format(filename), directory=directory)

@dataclass
class Node:
    name: str
    type: str = None
    gender: str = None
    num_pins: int = None
    pinout: List[Any] = field(default_factory=list)
    show_name: bool = False
    show_num_pins: bool = False

    def __post_init__(self):
        self.ports_left = False
        self.ports_right = False
        self.loops = []

        if self.pinout:
            if self.num_pins is not None:
                raise Exception('You cannot specify both pinout and num_pins')
        else:
            if not self.num_pins:
                self.num_pins = 1
            self.pinout = ['',] * self.num_pins

    def loop(self, from_pin, to_pin):
        self.loops.append((from_pin, to_pin))

@dataclass
class Cable:
    name: str
    mm2: float = None
    awg: int = None
    show_equiv: bool = False
    length: float = 0
    num_wires: int = None
    shield: bool = False
    colors: List[Any] = field(default_factory=list)
    color_code: str = None
    show_name: bool = False
    show_pinout: bool = False
    show_num_wires: bool = True

    def __post_init__(self):
        if self.mm2 and self.awg:
            raise Exception('You cannot define both mm2 and awg!')
        self.connections = []

        if self.num_wires: # number of wires explicitly defined
            if self.colors: # use custom color palette (partly or looped if needed)
                pass
            elif self.color_code: # use standard color palette (partly or looped if needed)
                if self.color_code not in COLOR_CODES:
                    raise Exception('Unknown color code')
                self.colors = COLOR_CODES[self.color_code]
            else: # no colors defined, add dummy colors
                self.colors = [''] * self.num_wires

            # make color code loop around if more wires than colors
            if self.num_wires > len(self.colors):
                 m = self.num_wires // len(self.colors) + 1
                 self.colors = self.colors * int(m)
            # cut off excess after looping
            self.colors = self.colors[:self.num_wires]

        else: # num_wires implicit in length of color list
            if not self.colors:
                raise Exception('Unknown number of wires. Must specify num_wires or colors (implicit length)')
            self.num_wires = len(self.colors)

    def connect(self, from_name, from_pin, via_pin, to_name, to_pin):
        from_pin = int2tuple(from_pin)
        via_pin  = int2tuple(via_pin)
        to_pin   = int2tuple(to_pin)
        if len(from_pin) != len(to_pin):
            raise Exception('from_pin must have the same number of elements as to_pin')
        for i, x in enumerate(from_pin):
            self.connections.append((from_name, from_pin[i], via_pin[i], to_name, to_pin[i]))

    def connect_all_straight(self, from_name, to_name):
        self.connect(from_name, 'auto', 'auto', to_name, 'auto')

def nested(input):
    l = []
    for x in input:
        if isinstance(x, list):
            if len(x) > 0:
                n = nested(x)
                if n != '':
                    l.append('{' + n + '}')
        else:
            if x is not None:
                if x != '':
                    l.append(str(x))
    s = '|'.join(l)
    return s

def int2tuple(input):
    if isinstance(input, tuple):
        output = input
    else:
        output = (input,)
    return output

def translate_color(input, color_mode):
    if input == '':
        output = ''
    else:
        if color_mode == 'full':
            output = color_full[input].lower()
        elif color_mode == 'FULL':
            output = color_hex[input].upper()
        elif color_mode == 'hex':
            output = color_hex[input].lower()
        elif color_mode == 'HEX':
            output = color_hex[input].upper()
        elif color_mode == 'ger':
            output = color_ger[input].lower()
        elif color_mode == 'GER':
            output = color_ger[input].upper()
        elif color_mode == 'short':
            output = input.lower()
        elif color_mode == 'SHORT':
            output = input.upper()
        else:
            raise Exception('Unknown color mode')
    return output

def awg_equiv(mm2):
    awg_equiv_table = {
                        '0.09': 28,
                        '0.14': 26,
                        '0.25': 24,
                        '0.34': 22,
                        '0.5': 21,
                        '0.75': 20,
                        '1': 18,
                        '1.5': 16,
                        '2.5': 14,
                        '4': 12,
                        '6': 10,
                        '10': 8,
                        '16': 6,
                        '25': 4,
                        }
    k = str(mm2)
    if k in awg_equiv_table:
        return awg_equiv_table[k]
    else:
        return None
