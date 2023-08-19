import zlib
import sys
import struct
import math
import base64
import json

savegame_has_checksum=True
ATLASFALLEN_MAGIC=0x7A145F28


def print_usage():
    print("Usage: ")
    print("savegame_body extract_raw <sav file in> <raw body out>")
    print(" -> Extracts the raw body from a save file.")
    print("")
    print("savegame_body extract_json <sav file in> <json body out> {options}")
    print(" -> Extracts the body from a save file as json.")
    print(" Options:")
    print(" --skip-era: Skips processing the game-specific portion of the save game body. May help with bugs or new game versions.")
    print(" --keep-inner-json-as-string: Will export the inner json as a raw string, to produce a 1:1 representation down to the characters.")
    print("")
    print("savegame_body compose_raw <sav file in> <raw body in> <sav file out> {options}")
    print(" -> Replaces the body in a save file from raw data.")
    print(" Options:")
    print(" --compress: Compresses the contents.")
    print("")
    print("savegame_body compose_json <sav file in> <json body in> <sav file out> {options}")
    print(" -> Replaces the body in a save file from a json representation.")
    print(" Options:")
    print(" --compress: Compresses the contents.")
if len(sys.argv) < 2:
    print("Missing option.")
    print_usage()
    exit()
mode = sys.argv[1]
flags = set()
if mode == "extract_raw" or mode == "extract_json":
    if len(sys.argv) != 4:
        if len(sys.argv) < 4:
            print("Missing arguments.")
        else:
            ALLOWED_FLAGS = set(["--skip-era","--keep-inner-json-as-string"])
            for i in range(4, len(sys.argv)):
                arg = sys.argv[i].lower()
                if arg in ALLOWED_FLAGS:
                    flags.add(arg)
                else:
                    print("Unknown option argument '%s'" % arg)
                    print_usage()
                    exit()
elif mode == "compose_raw" or mode == "compose_json":
    if len(sys.argv) != 5:
        if len(sys.argv) < 5:
            print("Missing arguments.")
        else:
            ALLOWED_FLAGS = set(["--compress"])
            for i in range(5, len(sys.argv)):
                arg = sys.argv[i].lower()
                if arg in ALLOWED_FLAGS:
                    flags.add(arg)
                else:
                    print("Unknown option argument '%s'" % arg)
                    print_usage()
                    exit()
else:
    print_usage()
    exit()

def compute_checksum(data):
    # Matches 'sdbm' (http://www.cse.yorku.ca/~oz/hash.html#sdbm)
    sum = 0
    for i in range(len(data)):
        sum = ((sum*0x1003F)&0xFFFFFFFF) + data[i]
        sum = sum&0xFFFFFFFF
    return sum

class FledgeSerdes:
    def __init__(self, body_in=b'', keep_inner_json_as_string=False):
        self.offs=0
        self.body_in = body_in
        self.body_out=bytearray()
        self.keep_inner_json_as_string = keep_inner_json_as_string;
    def _serdes_int8(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+1] if (deser_in is None) else struct.pack(">b",deser_in)
        self.offs+=1
        return struct.unpack(">b", self.body_out[-1:])[0]
    def _serdes_uint8(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+1] if (deser_in is None) else struct.pack(">B",deser_in)
        self.offs+=1
        return struct.unpack(">B", self.body_out[-1:])[0]
    def _serdes_int16(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+2] if (deser_in is None) else struct.pack(">h",deser_in)
        self.offs+=2
        return struct.unpack(">h", self.body_out[-2:])[0]
    def _serdes_uint16(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+2] if (deser_in is None) else struct.pack(">H",deser_in)
        self.offs+=2
        return struct.unpack(">H", self.body_out[-2:])[0]
    def _serdes_int32(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+4] if (deser_in is None) else struct.pack(">i",deser_in)
        self.offs+=4
        return struct.unpack(">i", self.body_out[-4:])[0]
    def _serdes_uint32(self, deser_in=None, ref_orig=None):
        if ref_orig is not None:
            ref_orig[0] = 0 if (self.body_in is None) else struct.unpack(">I", self.body_in[self.offs:self.offs+4])[0]
        self.body_out += self.body_in[self.offs:self.offs+4] if (deser_in is None) else struct.pack(">I",deser_in)
        self.offs+=4
        return struct.unpack(">I", self.body_out[-4:])[0]
    def _serdes_int64(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+8] if (deser_in is None) else struct.pack(">q",int(deser_in))
        self.offs+=8
        return str(struct.unpack(">q", self.body_out[-8:])[0]) #JSON numbers only fit 53 int bits.
    def _serdes_uint64(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+8] if (deser_in is None) else struct.pack(">Q",int(deser_in))
        self.offs+=8
        return str(struct.unpack(">Q", self.body_out[-8:])[0]) #JSON numbers only fit 53 int bits.
    def _serdes_bool(self, deser_in=None):
        ret = self._serdes_uint32(None if (deser_in is None) else (1 if (deser_in == True) else 0))
        if ret > 1:
            raise ValueError("bool representation is not in [0,1]")
        return ret != 0
    def _check_nan(val):
        if math.isnan(val):
            raise ValueError("float/double is NaN") #There are lots of possible NaN encodings, the json representation wouldn't be precise anymore.
        return val
    def _serdes_float(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+4] if (deser_in is None) else struct.pack(">f",deser_in)
        self.offs+=4
        return FledgeSerdes._check_nan(struct.unpack(">f", self.body_out[-4:])[0])
    def _serdes_double(self, deser_in=None):
        self.body_out += self.body_in[self.offs:self.offs+8] if (deser_in is None) else struct.pack(">d",deser_in)
        self.offs+=8
        return FledgeSerdes._check_nan(struct.unpack(">d", self.body_out[-8:])[0])
    def _serdes_string(self, deser_in=None, set_stringflag=True):
        if deser_in is not None:
            deser_in = deser_in.encode('utf8') #Assuming utf8 is correct
        str_len_orig = [0]
        str_len = self._serdes_uint32(None if (deser_in is None) else (len(deser_in) | (0x80000000 if set_stringflag else 0)), str_len_orig)
        str_len_orig = str_len_orig[0]
        if (str_len & 0x80000000) == 0 and set_stringflag:
            raise ValueError("string flag is not as expected")
        str_len = str_len & ~0x80000000
        str_len_padded = ((str_len) + 3) & ~3
        if deser_in is None:
            self.body_out += self.body_in[self.offs:self.offs+str_len_padded]
        else:
            self.body_out += deser_in
            self.body_out += b'\x00' * (str_len_padded - str_len)
        self.offs+=((~0x80000000 & str_len_orig) + 3) & ~3
        for i in range(str_len, str_len_padded):
            if self.body_out[len(self.body_out)-str_len_padded+i] != 0:
                raise ValueError("string is not zero-padded correctly")
        return self.body_out[len(self.body_out)-str_len_padded:len(self.body_out)-str_len_padded+str_len].decode('utf8') #Assuming utf8 is correct
        
    def _serdes_binary_unaligned(self, bin_len_in, deser_in=None): #Helper for rest
        if deser_in is not None:
            deser_in = base64.b64decode(deser_in) if isinstance(deser_in,str) else deser_in
            bin_len_written = len(deser_in)
            self.body_out += deser_in
        else:
            bin_len_written=bin_len_in
            self.body_out += self.body_in[self.offs:self.offs+bin_len_written]
        self.offs += bin_len_in
        return base64.b64encode(self.body_out[len(self.body_out)-bin_len_written:]).decode('utf8')
    def _serdes_binary_aligned(self, bin_len_in, deser_in=None):
        if deser_in is not None:
            deser_in = base64.b64decode(deser_in) if isinstance(deser_in,str) else deser_in
            bin_len_actual = len(deser_in)
            if (len(deser_in) & 3) != 0:
                deser_in += b'\x00' * (3 - ((len(deser_in) + 3) & 3))
            bin_len_written = len(deser_in)
            if len(deser_in) != ((bin_len_actual+3)&~3):
                raise ValueError("padded binary length does not match up")
            self.body_out += deser_in
        else:
            bin_len_actual=bin_len_in
            bin_len_written=((bin_len_in+3) & ~3)
            self.body_out += self.body_in[self.offs:self.offs+bin_len_written]
        self.offs += ((bin_len_in+3) & ~3)
        for i in range(bin_len_actual, bin_len_written):
            if self.body_out[len(self.body_out)-bin_len_written+i] != 0:
                raise ValueError("binary is not zero-padded correctly")
        return base64.b64encode(self.body_out[len(self.body_out)-bin_len_written:len(self.body_out)-bin_len_written+bin_len_actual]).decode('utf8')
    def _serdes_genericarray(self, deser_in, fn): #Helper to generically support 'uint32 len, datatype[len] data' arrays without alignment.
        deser_out = []
        offs_bak = self.offs
        out_len = self._serdes_uint32(None if (deser_in is None) else len(deser_in))
        for i in range(out_len):
            deser_out.append(fn(None if (deser_in is None) else deser_in[i]))
        if deser_in is not None and self.body_in is not None:
            self.offs = offs_bak
            self._serdes_genericarray(None) #Make sure self.offs goes forward by the original array size.
        return deser_out
    def _serdes_ref(self, deser_in=None, enable_ref_string=True):
        if deser_in is None:
            deser_in = [None,None,None,None]
        deser_out = [0,0,0]
        deser_out[0] = self._serdes_uint32(deser_in[0])
        deser_out[1] = self._serdes_uint64(deser_in[1])
        deser_out[2] = self._serdes_bool(deser_in[2])
        if enable_ref_string:
            deser_out.append(self._serdes_string(deser_in[3]))
        return deser_out
    def _serdes_name32(self, deser_in=None):
        if deser_in is None:
            deser_in = [None,None,None]
        deser_out = [0,0,0]
        deser_out[0] = '0x%08x'%self._serdes_uint32(None if (deser_in[0] is None) else int(deser_in[0],0))
        deser_out[1] = self._serdes_uint32(deser_in[1])
        deser_out[2] = self._serdes_bool(deser_in[2])
        return deser_out
    def _serdes_degree(self, deser_in=None):
        return self._serdes_float(deser_in)
    def _serdes_radian(self, deser_in=None):
        return self._serdes_float(deser_in)
    def _serdes_vec2(self, deser_in=None):
        if deser_in is None:
            deser_in = [None,None]
        deser_out = [0,0]
        deser_out[0] = self._serdes_float(deser_in[0])
        deser_out[1] = self._serdes_float(deser_in[1])
        return deser_out
    def _serdes_vec3(self, deser_in=None):
        if deser_in is None:
            deser_in = [None,None,None]
        deser_out = [0,0,0]
        deser_out[0] = self._serdes_float(deser_in[0])
        deser_out[1] = self._serdes_float(deser_in[1])
        deser_out[2] = self._serdes_float(deser_in[2])
        return deser_out
    def _serdes_vec4(self, deser_in=None):
        if deser_in is None:
            deser_in = [None,None,None,None]
        deser_out = [0,0,0,0]
        deser_out[0] = self._serdes_float(deser_in[0])
        deser_out[1] = self._serdes_float(deser_in[1])
        deser_out[2] = self._serdes_float(deser_in[2])
        deser_out[3] = self._serdes_float(deser_in[3])
        return deser_out
    def _serdes_rotate(self, deser_in=None):
        return self._serdes_vec3(deser_in)
    def _serdes_quat(self, deser_in=None):
        return self._serdes_vec4(deser_in)
    def _serdes_color(self, deser_in=None):
        return self._serdes_vec4(deser_in)
    def _serdes_udim(self, deser_in=None):
        return self._serdes_vec2(deser_in)
    def _serdes_uvector2(self, deser_in=None):
        if deser_in is None:
            deser_in = [None,None]
        deser_out = [0,0]
        deser_out[0] = self._serdes_udim(deser_in[0])
        deser_out[1] = self._serdes_udim(deser_in[1])
        return deser_out
    def _serdes_rect(self, deser_in=None):
        deser_out = {}
        deser_out["uint16 a"] = self._serdes_uint16(None if (deser_in is None) else deser_in[i]["uint16 a"])
        deser_out["uint16 b"] = self._serdes_uint16(None if (deser_in is None) else deser_in[i]["uint16 b"])
        return deser_out
    def _serdes_curve(self, deser_in=None):
        #Curve array element size: 28 bytes
        return self._serdes_genericarray(deser_in, lambda val: {
            "float a": self._serdes_float(None if (val is None) else val["float a"]),
            "vec2 b": self._serdes_vec2(None if (val is None) else val["vec2 b"]),
            "vec2 c": self._serdes_vec2(None if (val is None) else val["vec2 c"]),
            "vec2 d": self._serdes_vec2(None if (val is None) else val["vec2 d"])
        })
    def _serdes_void_or_null(self, deser_in=None):
        return None
    def _serdes_variantarray(self, deser_in=None):
        return self._serdes_genericarray(deser_in, lambda val:self._serdes_variant(val))
    def _serdes_variantdictionary(self, deser_in=None):
        return self._serdes_genericarray(deser_in, lambda val: {
            'string key': self._serdes_string(None if (val is None) else val['string key']),
            'Variant value': self._serdes_variant(None if (val is None) else val['Variant value'])
        })
    
    def __init_const__():
        global _variant_typeinfo_lookup
        global _variant_typename_reverse_lookup
        _variant_typeinfo_lookup=[(None,None),
            ("bool", FledgeSerdes._serdes_bool), #1
            ("int32", FledgeSerdes._serdes_int32), #2
            ("int8", FledgeSerdes._serdes_int8), #3
            ("uint8", FledgeSerdes._serdes_uint8), #4
            ("uint16", FledgeSerdes._serdes_uint16), #5
            ("uint32", FledgeSerdes._serdes_uint32), #6
            ("uint64", FledgeSerdes._serdes_uint64), #7
            ("float", FledgeSerdes._serdes_float), #8
            ("Degree", FledgeSerdes._serdes_degree), #9
            ("Radian", FledgeSerdes._serdes_radian), #10
            ("vec2", FledgeSerdes._serdes_vec2), #11
            ("vec3", FledgeSerdes._serdes_vec3), #12
            ("vec4", FledgeSerdes._serdes_vec4), #13
            ("Color", FledgeSerdes._serdes_color), #14
            ("Rotate", FledgeSerdes._serdes_rotate), #15
            ("quat", FledgeSerdes._serdes_quat), #16
            ("UDim", FledgeSerdes._serdes_udim), #17
            ("UVector2", FledgeSerdes._serdes_uvector2), #18
            ("Rect", FledgeSerdes._serdes_rect), #19
            ("Name32", FledgeSerdes._serdes_name32), #20
            ("Ref", FledgeSerdes._serdes_ref), #21
            ("void_or_null", FledgeSerdes._serdes_void_or_null), #22
            ("VariantArray", FledgeSerdes._serdes_variantarray), #23
            ("VariantDictionary", FledgeSerdes._serdes_variantdictionary), #24
            ("Curve", FledgeSerdes._serdes_curve) #25
        ]
        _variant_typename_reverse_lookup={_variant_typeinfo_lookup[typeid][0]:typeid for typeid in range(1,len(_variant_typeinfo_lookup))}
    
    def _typename_to_id(typename):
        if typename in _variant_typename_reverse_lookup:
            return _variant_typename_reverse_lookup[typename]
        raise ValueError("Variant typename '%s' unknown" % typename)
        return 0
    def _typeid_to_typeinfo(typeid):
        if typeid > len(_variant_typeinfo_lookup) or (_variant_typeinfo_lookup[typeid] is None):
            raise ValueError("Variant typeid %d unknown" % typeid)
        return _variant_typeinfo_lookup[typeid]
    def _serdes_variant(self, deser_in=None):
        offs_bak = self.offs
        
        deser_in_typeid = None if (deser_in is None) else FledgeSerdes._typename_to_id(next(iter(deser_in.keys())))        
        out_typeinfo = FledgeSerdes._typeid_to_typeinfo( self._serdes_uint32(deser_in_typeid) )
        
        deser_out={out_typeinfo[0] : out_typeinfo[1](self,None if (deser_in is None) else deser_in[out_typeinfo[0]])}
        
        if deser_in is not None and self.body_in is not None:
            self.offs = offs_bak
            self._serdes_variant(None) #Make sure self.offs goes forward by the original variant size.
        
        return deser_out
    
    
    def _fieldname_short(fieldname):
        return fieldname.split('_')[0] #Name format: "<type> field<number>_"
    def _opt_map_with_short_fieldnames(map_in):
        return None if (map_in is None) else {FledgeSerdes._fieldname_short(key):map_in[key] for key in map_in.keys()}
    def _opt_map_select_with_shortname(map_in, shortname):
        return None if (map_in is None) else map_in[[fullname for fullname in map_in.keys() if shortname==FledgeSerdes._fieldname_short(fullname)][0]]
    def _serdes_field(self, deser_out, deser_in_shortnames, fieldname, fieldfn):
        #offs_pre = self.offs
        fieldname_short=type(self)._fieldname_short(fieldname)
        ret = fieldfn(None if (deser_in_shortnames is None) else deser_in_shortnames[fieldname_short])
        #print("_serdes_field: @0x%x - '%s' = %s" % (offs_pre, fieldname, str(ret)))
        deser_out[fieldname] = ret
        return ret
    def _serdes_arrayfield(self, deser_out, deser_in_shortnames, fieldname, elemfn):
        return self._serdes_field(deser_out, deser_in_shortnames, fieldname,
            lambda deser_in: self._serdes_genericarray(deser_in, elemfn))
    def _serdes_rest(self, deser_out, deser_in_shortnames, fieldname):
        fieldname_short=type(self)._fieldname_short(fieldname)
        if (self.body_in is not None) and self.offs > len(self.body_in):
            raise ValueError("Remaining input data size is negative")
        ret = self._serdes_binary_unaligned(
            0 if (self.body_in is None) else (len(self.body_in) - self.offs),
            None if (deser_in_shortnames is None) else deser_in_shortnames[fieldname_short])
        deser_out[fieldname] = ret
        return ret
    
    def _serdes_json_asstring(self, keep_as_string, deser_in=None): #Helper for the JSON data in FledgeCore::SaveGameDesc
        json_str = self._serdes_string(None if (deser_in is None) else (deser_in if isinstance(deser_in,str) else json.dumps(deser_in, separators=(',', ':'))), False)
        return json_str if keep_as_string else json.loads(json_str)
    
    def serdes_body(self, deser_in=None):
        deser_in_shortnames = type(self)._opt_map_with_short_fieldnames(deser_in) #Replace all field names by short names.
        deser_out={}
        #Leave 9 free numbers in between each field name to enable some naming consistency with future file formats.
        self._serdes_field(deser_out, deser_in_shortnames, "Name32 fieldCore00", self._serdes_name32)
        self._serdes_field(deser_out, deser_in_shortnames, "Name32 fieldCore10", self._serdes_name32)
        self._serdes_field(deser_out, deser_in_shortnames, "string fieldCore20", self._serdes_string)
        body_format = self._serdes_field(deser_out, deser_in_shortnames, "uint32 fieldCore30_format", self._serdes_uint32)
        if body_format > 2:
            print("Warning: Unknown Fledge::Core::SaveGameDesc binary format %d. Using raw data instead." % body_format)
        if body_format > 2 or ((deser_in is not None) and "binary-as-base64 rest after fieldCore30" in deser_in_shortnames):
            self._serdes_rest(deser_out, deser_in_shortnames, "binary-as-base64 rest after fieldCore30")
            return deser_out
        self._serdes_field(deser_out, deser_in_shortnames, "uint8 fieldCore40", self._serdes_uint8)
        self._serdes_field(deser_out, deser_in_shortnames, "uint64 fieldCore50", self._serdes_uint64)
        if body_format < 1:
            self._serdes_field(deser_out, deser_in_shortnames, "uint16 fieldCore60", self._serdes_uint16)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldCore70", self._serdes_bool)
        if body_format >= 2:
            self._serdes_field(deser_out, deser_in_shortnames, "uint32 fieldCore80", self._serdes_uint32)
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldCore90", lambda val: {
            "uint64 field00": self._serdes_uint64(type(self)._opt_map_select_with_shortname(val, "uint64 field00")),
            "bool field10": self._serdes_bool(type(self)._opt_map_select_with_shortname(val, "bool field10"))
        })
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldCore100", lambda val: {
            "Name32 field00": self._serdes_name32(type(self)._opt_map_select_with_shortname(val, "Name32 field00")),
            "int32 field10": self._serdes_int32(type(self)._opt_map_select_with_shortname(val, "int32 field10"))
        })
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldCore110", lambda val: {
            "Name32 field00": self._serdes_name32(type(self)._opt_map_select_with_shortname(val, "Name32 field00")),
            "bool field10": self._serdes_bool(type(self)._opt_map_select_with_shortname(val, "bool field10"))
        })
        self._serdes_field(deser_out, deser_in_shortnames, "string fieldCore120_json", lambda val: self._serdes_json_asstring(self.keep_inner_json_as_string,val))
        
        return deser_out
FledgeSerdes.__init_const__()
class EraSerdes(FledgeSerdes): #Atlas Fallen
    def __init__(self, header, body_in=None, skip_era=False, keep_inner_json_as_string=False):
        FledgeSerdes.__init__(self, body_in, keep_inner_json_as_string)
        self.era_format = struct.unpack("I", header[0:4])[0]
        self.skip_era = skip_era
    
    def _serdes_constantsize_binary(self, size, deser_in=None):
        out_offs_pre = len(self.body_out)
        ret = self._serdes_binary_aligned(size, deser_in)
        written_len = len(self.body_out) - out_offs_pre
        if written_len != size:
            raise ValueError("Unexpected size of constant size field: Got %d bytes, expected %d" % (written_len, size))
        return ret
    def _serdes_binaryarray_aligned(self, deser_in=None):
        if deser_in is not None:
            deser_in = base64.b64decode(deser_in) if isinstance(deser_in,str) else deser_in
        bin_len_orig = [0]
        bin_len_actual = self._serdes_uint32(None if (deser_in is None) else len(deser_in), bin_len_orig)
        bin_len_orig = bin_len_orig[0]
        out_offs_pre = len(self.body_out)
        ret = self._serdes_binary_aligned(bin_len_orig, deser_in)
        written_len = len(self.body_out) - out_offs_pre
        if written_len != ((bin_len_actual+3)&~3):
            raise ValueError("Unexpected size of aligned binary array: Got %d bytes, expected %d" % (written_len, ((bin_len_actual+3)&~3)))
        return ret
    def _serdes_constantlen_array(self, const_len, deser_in, fieldfn):
        deser_out = [None] * const_len
        for i in range(const_len):
            deser_out[i] = fieldfn(None if (deser_in is None) else deser_in[i])
        return deser_out
    
    def serdes_body(self, deser_in=None):
        deser_in_shortnames = type(self)._opt_map_with_short_fieldnames(deser_in) #Replace all field names by short names.
        deser_out=FledgeSerdes.serdes_body(self, deser_in)
        if self.skip_era or self.era_format > 0x29:
            print("Warning: Unsupported Era::SaveGameDesc binary format 0x%02x. Using raw data instead." % self.era_format)
        if self.skip_era or self.era_format > 0x29 or ((deser_in is not None) and "binary-as-base64 rest after Core" in deser_in_shortnames):
            self._serdes_rest(deser_out, deser_in_shortnames, "binary-as-base64 rest after Core")
            return deser_out
        self._serdes_field(deser_out, deser_in_shortnames, "binary[96]-as-base64 fieldEra00", lambda val: self._serdes_constantsize_binary(96, val))
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldEra10", lambda val: {
            "uint64 field00": self._serdes_uint64(type(self)._opt_map_select_with_shortname(val, "uint64 field00")),
            "uint8 field10": self._serdes_uint8(type(self)._opt_map_select_with_shortname(val, "uint8 field10"))
        })
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldEra20", lambda val: {
            "Name32 field00_ui_map_type": self._serdes_name32(type(self)._opt_map_select_with_shortname(val, "Name32 field00")),
            #"uint32[0x10000] field10_image": self._serdes_constantlen_array(0x10000, type(self)._opt_map_select_with_shortname(val, "uint32[0x10000] field10"), self._serdes_uint32)
            "uint32[0x10000]-as-base64 field10_image": self._serdes_constantsize_binary(4*0x10000, type(self)._opt_map_select_with_shortname(val, "uint32[0x10000]-as-base64 field10"))
        })
        self._serdes_field(deser_out, deser_in_shortnames, "Name32 fieldEra30_ui_map_type", self._serdes_name32)
        self._serdes_field(deser_out, deser_in_shortnames, "vec3 fieldEra40_pos", self._serdes_vec3)
        self._serdes_field(deser_out, deser_in_shortnames, "float fieldEra50", self._serdes_float)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra60", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra70", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra80", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra90", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra100", self._serdes_bool)
        if self.era_format >= 0x27:
            self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra110", self._serdes_bool)
        if self.era_format >= 0x28:
            self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra120", self._serdes_bool)
            self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra130", self._serdes_bool)
            self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra140", self._serdes_bool)
            self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra150", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra160", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra170", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "uint8 fieldEra180", self._serdes_uint8)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra190", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "uint8 fieldEra200", self._serdes_uint8)
        self._serdes_field(deser_out, deser_in_shortnames, "bool fieldEra210", self._serdes_bool)
        self._serdes_field(deser_out, deser_in_shortnames, "uint8 fieldEra220", self._serdes_uint8)
        if self.era_format >= 0x26:
            self._serdes_field(deser_out, deser_in_shortnames, "int32 fieldEra230", self._serdes_int32)
        if self.era_format < 0x29:
            self._serdes_field(deser_out, deser_in_shortnames, "uint32 fieldEra240", self._serdes_int32)
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "uint32[] fieldEra250", self._serdes_uint32)
        self._serdes_arrayfield(deser_out, deser_in_shortnames, "uint32[] fieldEra260", self._serdes_uint32)
        if self.era_format >= 0x18:
            self._serdes_arrayfield(deser_out, deser_in_shortnames, "Name32[] fieldEra270_buffs", self._serdes_name32)
        self._serdes_field(deser_out, deser_in_shortnames, "binary-as-base64 fieldEra280", self._serdes_binaryarray_aligned)
        if self.era_format >= 0x1B:
            self._serdes_arrayfield(deser_out, deser_in_shortnames, "Name32[] fieldEra290_npc_voices", self._serdes_name32)
        if self.era_format >= 0x25:
            self._serdes_field(deser_out, deser_in_shortnames, "uint32 fieldEra300_mapdata_1", self._serdes_uint32)
            self._serdes_arrayfield(deser_out, deser_in_shortnames, "array fieldEra310_mapdata_2", lambda val: {
                "uint8 field00": self._serdes_uint8(type(self)._opt_map_select_with_shortname(val, "uint8 field00")),
                "uint8 field10": self._serdes_uint8(type(self)._opt_map_select_with_shortname(val, "uint8 field10")),
                "Variant field20": self._serdes_variant(type(self)._opt_map_select_with_shortname(val, "Variant field20")),
                "Variant field30": self._serdes_variant(type(self)._opt_map_select_with_shortname(val, "Variant field30")),
                "Variant field40": self._serdes_variant(type(self)._opt_map_select_with_shortname(val, "Variant field40")),
                "vec3 field50": self._serdes_vec3(type(self)._opt_map_select_with_shortname(val, "vec3 field50"))
            })
        if ((self.body_in is not None) and self.offs < len(self.body_in)) or ((deser_in is not None) and "binary-as-base64 rest after Era" in deser_in_shortnames):
            print("Warning: Encountered data after the expected end! Processing as unknown binary suffix.")
            self._serdes_rest(deser_out, deser_in_shortnames, "binary-as-base64 rest after Era")
        if ((self.body_in is not None) and self.offs != len(self.body_in)):
            print("Error: The input position after processing is %d, but the actual size is %d! Expect invalid results." % (self.offs, len(self.body_in)))
        return deser_out

with open(sys.argv[2], 'rb') as fin:
    savegame_data=fin.read()
    pos=0
    headerheader_magic = struct.unpack("I",savegame_data[pos:pos+4])[0]
    pos += 4
    if headerheader_magic != ATLASFALLEN_MAGIC:
        print("No valid Atlas Fallen savegame (magic mismatch: got %08X, expected %08X)" % (headerheader_magic, ATLASFALLEN_MAGIC))
        exit()
    checksum = 0
    if savegame_has_checksum:
        checksum = struct.unpack("I",savegame_data[pos:pos+4])[0]
        pos += 4
    header_size = struct.unpack("I",savegame_data[pos:pos+4])[0]
    pos += 4
    header = savegame_data[pos:pos+header_size]
    pos += header_size
    
    body_is_compressed = struct.unpack("I",savegame_data[pos:pos+4])[0]
    body_compressed_size = struct.unpack("I",savegame_data[pos+4:pos+8])[0]
    body_decompressed_size = struct.unpack("I",savegame_data[pos+8:pos+12])[0]
    pos += 12
    
    if body_is_compressed != 0:
        if pos + body_compressed_size != len(savegame_data):
            print("File size mismatch (compressed body size %08X, but have %08X to EOF)" % (body_compressed_size, len(savegame_data) - pos))
        decompressor = zlib.decompressobj(wbits=15)
        body = decompressor.decompress(savegame_data[pos:pos+body_compressed_size])
        body += decompressor.flush()
        if len(body) != body_decompressed_size:
            print("Warning: Advertised body size %d does not match the decompressed size %d!" % (body_decompressed_size, len(body)))
    else:
        if pos + body_decompressed_size != len(savegame_data):
            print("File size mismatch (body size %08X, but have %08X to EOF)" % (body_decompressed_size, len(savegame_data) - pos))
        body = savegame_data[pos:pos+body_decompressed_size]
    computed_checksum = compute_checksum(body)
    if savegame_has_checksum and checksum != computed_checksum:
        print("Checksum mismatch (header says %08X, but computed %08X)" % (checksum, computed_checksum))
    
    if mode == "extract_raw":
        with open(sys.argv[3], 'wb') as fout:
            fout.write(body)
    if mode == "extract_json":
        with open(sys.argv[3], 'wb') as fout:
            serdes = EraSerdes(header, body, "--skip-era" in flags, "--keep-inner-json-as-string" in flags)
            body_json = json.dumps(serdes.serdes_body(None), indent=4)
            fout.write(body_json.encode('utf8'))
    if mode.startswith("compose_"):
        with open(sys.argv[3], 'rb') as fin_body:
            if mode == "compose_raw":
                body = fin_body.read()
            if mode == "compose_json":
                body_json = json.loads(fin_body.read().decode('utf8'))
                serdes = EraSerdes(header, None)
                serdes.serdes_body(body_json)
                body = serdes.body_out
        computed_checksum = compute_checksum(body)
        with open(sys.argv[4], 'wb') as fout:
            fout.write(struct.pack("III", ATLASFALLEN_MAGIC, computed_checksum, header_size))
            fout.write(header)
            if "--compress" in flags:
                #Default compression level can produce identical files to the game
                # (depending on zlib version - game uses zlib 1.2.3; is the case for Python 3.9 and 3.11, probably not for future versions - https://github.com/python/cpython/issues/91349 )
                compressor = zlib.compressobj(wbits=15) 
                body_compressed = compressor.compress(body)
                body_compressed += compressor.flush()
                fout.write(struct.pack("III", 1, len(body_compressed), len(body)))
                fout.write(body_compressed)
            else:
                fout.write(struct.pack("III", 0, len(body), len(body)))
                fout.write(body)

print("Done")
