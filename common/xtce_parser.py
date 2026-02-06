import xml.etree.ElementTree as ET
import struct

class XtceParser:
    def __init__(self, xml_filename: str):
        self.packet_map = {}
        self.command_map = {}
        self.namespaces = {'xtce': 'http://www.omg.org/space/xtce'}
        self._load_xml(xml_filename)

    def _load_xml(self, filename: str):
        tree = ET.parse(filename)
        root = tree.getroot()

        self._load_telemetry(root)
        self._load_commands(root)

    def _get_struct_char(self, root, type_ref):
        float_type = root.find(f".//xtce:FloatParameterType[@name='{type_ref}']", self.namespaces)

        if float_type is not None:
            encoding = float_type.find(".//xtce:FloatDataEncoding", self.namespaces)
            if encoding is not None:
                bits = int(encoding.attrib['sizeInBits'])
                if bits == 32:
                    return 'f'
                elif bits == 64:
                    return 'd'

        # Future: Add IntegerParameterType logic here
        return None

    def _load_telemetry(self, root):
        for container in root.findall(".//xtce:SequenceContainer", self.namespaces):
            packet_name = container.attrib['name']

            match_criteria = container.find(".//xtce:Comparison[@parameterRef='APID']", self.namespaces)
            if match_criteria is None: continue

            apid = int(match_criteria.attrib['value'])

            struct_fmt = "!"
            param_names = []

            entry_list = container.find("xtce:EntryList", self.namespaces)
            for entry in entry_list.findall("xtce:ParameterRefEntry", self.namespaces):
                param_name = entry.attrib['parameterRef']

                param_def = root.find(f".//xtce:TelemetryParameter[@name='{param_name}']", self.namespaces)
                type_ref = param_def.attrib['parameterTypeRef']

                fmt_char = self._get_struct_char(root, type_ref)
                if fmt_char:
                    struct_fmt += fmt_char
                    param_names.append(param_name)
                else:
                    print(f"⚠️ Warning: Unknown type for param {param_name}")


            print(f"Loaded XML Definition for APID {apid}: {packet_name} -> {struct_fmt}")
            self.packet_map[apid] = {
                "format": struct_fmt,
                "names": param_names,
            }

    def _load_commands(self, root):
        for meta_cmd in root.findall(".//xtce:MetaCommand", self.namespaces):
            cmd_name = meta_cmd.attrib['name']

            cmd_container = meta_cmd.find(".//xtce:CommandContainer", self.namespaces)
            if cmd_container is None: continue

            match_criteria = cmd_container.find(".//xtce:Comparison[@parameterRef='APID']", self.namespaces)
            if match_criteria is None: continue

            apid = int(match_criteria.attrib['value'])
            entry_list = cmd_container.find(".//xtce:EntryList", self.namespaces)

            segments = []
            if entry_list is None: continue

            for entry in entry_list:
                if entry.tag.endswith("FixedValueEntry"):
                    hex_value = entry.find("xtce:BinaryHex", self.namespaces).text
                    fixed_bytes = bytes.fromhex(hex_value)
                    segments.append({"type": "fixed", "val": fixed_bytes})

                elif entry.tag.endswith("ArgumentRefEntry"):
                    arg_ref = entry.attrib['argumentRef']

                    arg_def = meta_cmd.find(f".//xtce:Argument[@name='{arg_ref}']", self.namespaces)
                    if arg_def:
                        type_ref = arg_def.attrib['argumentTypeRef']
                        fmt_char = self._get_struct_char(root, type_ref)

                        if fmt_char:
                            segments.append({"type": "arg", "name": arg_ref, "fmt": fmt_char})


            print(f"Loaded Command: {cmd_name} (APID {apid}) -> args: {segments}")
            self.command_map[cmd_name] = {
                "apid": apid,
                "segments": segments,
            }

    def decode(self, apid: int, payload_bytes):
        if apid not in self.packet_map:
            print(f"Warning: No XML definition for APID {apid}.")
            return None

        def_data = self.packet_map[apid]
        fmt = def_data["format"]
        names = def_data["names"]

        try:
            values = struct.unpack(fmt, payload_bytes)
            return dict(zip(names, values))
        except struct.error as e:
            print(f"Decode Error for APID {apid}: {e}")
            return None

    def encode(self, command_name: str, **kwargs):
        if command_name not in self.command_map:
            print(f"Error: Unknown command: {command_name}")
            return None

        cmd_def = self.command_map[command_name]
        segments = cmd_def["segments"]

        payload = b''

        for segment in segments:
            if segment["type"] == "fixed":
                payload += segment["val"]

            elif segment["type"] == "arg":
                arg_name = segment["name"]
                if arg_name not in kwargs:
                    print(f"Error: Missing argument '{arg_name}' for command '{command_name}'")
                    return None

                val = kwargs[arg_name]
                try:
                    payload += struct.pack("!" + segment["fmt"], val)
                except struct.error as e:
                    print(f"Encode Error for {arg_name}: {e}")
                    return None

        return payload

    def get_command_apid(self, command_name: str):
        if command_name in self.command_map:
            return self.command_map[command_name]["apid"]
        return None



