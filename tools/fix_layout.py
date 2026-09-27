#!/usr/bin/env python3
"""Emit endpoint-specific GSDK metadata; upstream templates merge cluster layouts.

The stock 7.5.2 templates with ZAP 2026 deduplicate by cluster/attribute ID,
losing per-endpoint defaults and using the wrong attribute slice for differing
Electrical Measurement selections. Keep the SDK protocol code, but explicitly
emit its public attribute/cluster/endpoint table format from the reviewed ZAP.
"""
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
base=Path(__file__).resolve().parents[1]
z=json.loads((base/'firmware/config/zcl/zcl_config.zap').read_text())
properties=json.loads((base/'firmware/config/zcl/zcl-properties.json').read_text())
lengths={}
for filename in properties['xmlFile']:
    for root in properties['xmlRoot']:
        file=base/'firmware/config/zcl'/root/filename
        if not file.is_file(): continue
        tree=ET.parse(file)
        for c in tree.getroot().findall('cluster'):
            try: code=int(c.findtext('code'),16)
            except (ValueError,TypeError): continue
            for a in c.findall('attribute'):
                if a.get('side')=='server' and a.get('length'):
                    lengths[code,int(a.get('code'),16)]=int(a.get('length'))
        break
sizes={'int8u':1,'enum8':1,'boolean':1,'bitmap8':1,'int16u':2,'int16s':2,
       'enum16':2,'bitmap32':4,'float_single':4}
attrs=[]; cs=[]; eps=[]; defaults=bytearray(); reports=[]; layout=[]
max_size=1; total=0
for endpoint in z['endpoints']:
    ep=endpoint['endpointId']
    definition=z['endpointTypes'][endpoint['endpointTypeIndex']]
    cluster_start=len(cs); ep_size=0
    for c in sorted(definition['clusters'],key=lambda c:c['code']):
        if not c['enabled'] or c['side']!='server': continue
        start=len(attrs); size=0; attr_ids=[]; attr_info=[]
        for a in sorted(c['attributes'],key=lambda a:a['code']):
            if not a['included']: continue
            kind=a['type']; aid=a['code']; raw=a['defaultValue']
            if kind=='char_string':
                size_a=lengths[c['code'],aid]+1
                encoded=raw.encode('utf8')
                if len(encoded)>=size_a: raise ValueError(f'String too long: {raw}')
                # ProductLabel is immutable: reserve its actual length, not 64 bytes
                # per endpoint, while retaining the standard ZCL string encoding.
                if c['code']==0 and aid==0x000e:
                    size_a=len(encoded)+1
                data=bytes([len(encoded)])+encoded+bytes(size_a-1-len(encoded))
            else:
                size_a=sizes[kind]
                if kind=='float_single': data=struct.pack('<f',float(raw))
                else: data=(int(raw,0) & ((1<<(8*size_a))-1)).to_bytes(size_a,'little')
            if size_a<=2:
                value=f'(uint8_t*)0x{int.from_bytes(data,"little"):x}'
            else:
                offset=len(defaults); defaults.extend(data)
                value=f'(uint8_t*)&generatedDefaults[{offset}]'
            attrs.append(f'{{ 0x{aid:04x}, ZCL_{kind.upper()}_ATTRIBUTE_TYPE, {size_a}, 0, {{ {value} }} }}')
            attr_info.append(dict(id=aid,offset=size,size=size_a,kind=kind,default=raw))
            size+=size_a; max_size=max(max_size,size_a); attr_ids.append(aid)
            if a['reportable']:
                change=int(a['reportableChange'])
                if kind=='float_single':
                    resolution=next((x['defaultValue'] for x in c['attributes'] if x['code']==0x6a),'1')
                    change=struct.unpack('<I',struct.pack('<f',float(resolution)))[0]
                reports.append(f'{{ EMBER_ZCL_REPORTING_DIRECTION_REPORTED, {ep}, 0x{c["code"]:04x}, 0x{aid:04x}, CLUSTER_MASK_SERVER, 0, {a["minInterval"]}, {a["maxInterval"]}, {change} }}')
        cs.append(f'{{ 0x{c["code"]:04x}, (EmberAfAttributeMetadata*)&generatedAttributes[{start}], {len(attrs)-start}, {size}, CLUSTER_MASK_SERVER, NULL }}')
        layout.append(dict(endpoint=ep,cluster=c['code'],attribute_ids=attr_ids,attributes=attr_info,size=size,offset=total+ep_size))
        ep_size+=size
    eps.append(f'{{ (EmberAfCluster*)&generatedClusters[{cluster_start}], {len(cs)-cluster_start}, {ep_size} }}')
    total+=ep_size
macros={
 'GENERATED_DEFAULTS_COUNT':str(len(defaults)), 'GENERATED_ATTRIBUTE_COUNT':str(len(attrs)),
 'GENERATED_CLUSTER_COUNT':str(len(cs)), 'GENERATED_ENDPOINT_TYPE_COUNT':str(len(eps)),
 'ATTRIBUTE_LARGEST':str(max_size),'ATTRIBUTE_SINGLETONS_SIZE':'0','ATTRIBUTE_MAX_SIZE':str(total),
 'GENERATED_DEFAULTS':[', '.join(f'0x{x:02x}' for x in defaults[i:i+16]) for i in range(0,len(defaults),16)],
 'GENERATED_ATTRIBUTES':attrs,'GENERATED_CLUSTERS':cs,'GENERATED_ENDPOINT_TYPES':eps,
 'EMBER_AF_GENERATED_REPORTING_CONFIG_DEFAULTS':reports,
 'EMBER_AF_GENERATED_REPORTING_CONFIG_DEFAULTS_TABLE_SIZE':str(len(reports))}
path=base/'build/autogen/zap-config.h'
lines=path.read_text().splitlines(); output=[]; i=0
while i<len(lines):
    match=re.match(r'\s*#define\s+(\w+)\b',lines[i])
    if match and match[1] in macros:
        name=match[1]
        while lines[i].rstrip().endswith('\\'): i+=1
        value=macros[name]
        if isinstance(value,list):
            output += [f'#define {name} {{ \\']+['    '+x+', \\' for x in value]+['}']
        else: output.append(f'#define {name} ({value})')
    else: output.append(lines[i])
    i+=1
path.write_text('// Endpoint metadata corrected by tools/fix_layout.py (little-endian EFR32).\n'+'\n'.join(output)+'\n')
(base/'results/attribute-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
print(f'Layout: {len(attrs)} attributes, {len(cs)} clusters, {total} bytes RAM')
