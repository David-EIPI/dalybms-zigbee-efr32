#!/usr/bin/env python3
"""Generate standard ZCL endpoints and their C mapping from one source of truth."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from metrics import METRICS
BASE = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get('GSDK','/opt/silabs/efr32mg1-2026-09/tools/gecko-sdk-4.5.1'))
clusters = {}
for file in (SDK/'app/zcl').glob('*.xml'):
    try: root = ET.parse(file).getroot()
    except ET.ParseError: continue
    for c in root.findall('cluster'):
        if c.findtext('code'):
            try: clusters[int(c.findtext('code'),16)] = c
            except ValueError: pass

for filename in ('analog-input.xml', 'analog-value.xml'):
    for c in ET.parse(BASE/'firmware/config/zcl'/filename).getroot().findall('cluster'):
        clusters[int(c.findtext('code'),16)] = c

def attribute(code, name, dtype, default, report=False, singleton=False):
    return dict(name=name, code=code, mfgCode=None, side='server', type=dtype.lower(),
                included=1, storageOption='RAM', singleton=int(singleton), bounded=0,
                defaultValue=str(default), reportable=int(report), minInterval=30,
                maxInterval=300, reportableChange=1)

def cluster(code, selected):
    c = clusters[code]
    attrs = []
    for a in c.findall('attribute'):
        aid = int(a.get('code'),16)
        if a.get('side') != 'server' or aid not in selected: continue
        value, report = selected[aid]
        attrs.append(attribute(aid,a.text.strip(),a.get('type'),value,report))
        if code == 0xe:
            attrs[-1]['writable'] = a.get('writable') == 'true'
    attrs.append(attribute(0xfffd,'cluster revision','int16u','3' if code==0 else '1',singleton=True))
    return dict(name=c.findtext('name'),code=code,mfgCode=None,define=c.findtext('define'),
                side='server',enabled=1,attributes=attrs,commands=[])

SHORT_LABELS = {
    'Charge MOS active':'Chg MOS active',
    'Discharge MOS active':'Dsg MOS active',
    'Precharge MOS active':'Prechg MOS act',
    'Heater MOS active':'Heater MOS act',
    'Charge MOS command':'Chg MOS command',
    'Discharge MOS command':'Dsg MOS command',
    'Charge MOS overtemperature fault':'Chg MOS hot',
    'Charge MOS temperature sensing fault':'Chg MOS temp err',
    'Discharge MOS overtemperature fault':'Dsg MOS hot',
    'Discharge MOS temperature sensing fault':'Dsg MOS temp err',
    'Short circuit protection':'Short circuit',
    'Charge undervoltage fault':'Chg undervoltage',
    'Discharge overvoltage fault':'Dsg overvoltage',
    'AFE communication fault':'AFE link fault',
    'AFE sampling fault':'AFE sample fault',
    'Cell voltage sensing fault':'Cell sense fault',
    'Cell voltage wire disconnected':'Cell wire open',
    'Pack voltage sensing fault':'Pack sense fault',
    'Current sensing fault':'Current sens err',
    'Temperature sensing fault':'Temp sense fault',
    'Temperature probe disconnected':'Probe unplugged',
    'Discharge MOS fault':'Dsg MOS fault',
    'Precharge MOS fault':'Prechg MOS fault',
    'Precharge failure':'Precharge failed',
    'Current limiting active':'Current limiting',
    'BMS communication':'BMS link active',
    'Smart charger connected':'Charger linked',
    'Smart charger connection fault':'Charger link err',
    'Smart discharger connected':'Load linked',
    'Smart discharger connection fault':'Load link fault',
    'Parallel communication active':'Parallel linked',
    'Parallel communication fault':'Parallel fault',
    'Charge MOS disabled by bus':'Chg off by bus',
    'Discharge MOS disabled by bus':'Dsg off by bus',
    'Charge MOS disabled by switch':'Chg switch off',
    'Discharge MOS disabled by switch':'Dsg switch off',
}
kind_code = {'voltage':0xb04,'current':0xb04,'power':0xb04,'temperature':0x402,'analog':0xc,'binary':0xf}
kind_id = {k:i for i,k in enumerate(kind_code)}
def product_label(metric):
    name = metric['name']
    extrema={'Highest cell voltage':'Highest cell', 'Highest voltage cell':'Highest cell',
             'Lowest cell voltage':'Lowest cell', 'Lowest voltage cell':'Lowest cell',
             'Cell voltage spread':'Cell spread', 'Highest temperature':'Hottest probe',
             'Hottest probe':'Hottest probe', 'Lowest temperature':'Coldest probe',
             'Coldest probe':'Coldest probe'}
    if name in extrema:
        return extrema[name]
    if name.startswith(('Cell ', 'Probe ')) and name.split()[1].isdigit():
        return ' '.join(name.split()[:2])
    for prefix, label in [('Charge ', 'Pack charge'), ('Discharge ', 'Pack discharge'),
                          ('Balancing ', 'Balancer'), ('MOS ', 'BMS MOS'),
                          ('Board ', 'BMS board'), ('Heater ', 'Heater'), ('Fan ', 'Fan')]:
        if name.startswith(prefix):
            return label
    return 'Pack'

# Preserve electrical and general-input endpoint IDs; general inputs name themselves.
endpoint_labels = {1:'Pack', 2:'Pack charge', 3:'Pack discharge', 4:'Balancer',
                   **{5+i:f'Cell {i+1}' for i in range(8)},
                   13:'Highest cell', 14:'Lowest cell', 15:'Cell spread'}
endpoints = {ep:[] for ep in endpoint_labels}
counts = {}
rows = []
for original in METRICS:
    m=original.copy()
    code=kind_code[m['kind']]
    label=product_label(m)
    counts[code]=counts.get(code,0)+1
    k=m['kind']
    if code==0xb04:
        if m['name'].startswith('Pack '): ep=1
        elif m['name'].startswith('Charge '): ep=2
        elif m['name'].startswith('Discharge '): ep=3
        elif m['name']=='Balancing current': ep=4
        elif m['special']==3: ep=5+m['reg']
        else: ep={0x3e:13,0x40:14,0x42:15}[m['reg']]
    elif code==0x402:
        # Probe/temperature sources have no Description attribute of their own.
        ep=15+counts[code]
        endpoint_labels[ep]=label
    else:
        # Analog/Binary Input entities use Description, not the endpoint label.
        ep=counts[code]
    endpoints.setdefault(ep,[])
    endpoint_labels.setdefault(ep,'Pack')
    if code in (0xb04,0x402):
        assert endpoint_labels[ep]==label
    if code==0xb04:
        attr={'voltage':0x100,'current':0x103,'power':0x106}[k]
        mult={'voltage':0x200,'current':0x202,'power':0x204}[k]
        divisor=round(1/m['scale'])
        selected={0:(8,False),attr:('0x8000',True),mult:(1,False),mult+1:(divisor,False)}
    elif code==0x402:
        attr=0; divisor=100
        selected={0:('0x8000',True),1:(-4000,False),2:(12500,False)}
    else:
        attr=0x55; divisor=1
        # SDK descriptions have a 16-byte maximum; ENDPOINTS.md retains full labels.
        selected={0x1c:(m['name'] if k=='analog' else SHORT_LABELS.get(m['name'], m['name']),False),0x51:(0,False),0x55:(0,True),0x6f:(2,False),0x67:(7,False)}
        if k=='analog':
            selected.update({0x75:(m['unit'],False),0x6a:(m['scale'],False)})
    new_cluster=cluster(code,selected)
    existing=next((c for c in endpoints.setdefault(ep,[]) if c['code']==code),None)
    if existing:
        used={a['code'] for a in existing['attributes']}
        existing['attributes'].extend(a for a in new_cluster['attributes'] if a['code'] not in used)
    else:
        endpoints[ep].append(new_cluster)
    m.update(endpoint=ep,cluster=code,attribute=attr,divisor=divisor,product_label=label)
    rows.append(m)
for m in rows:
    m['product_label']=endpoint_labels[m['endpoint']]
endpoints[1].append(cluster(0xe, {
    0x1c:('Update interval',False), 0x51:(0,False), 0x55:(30,True),
    0x67:(0,False), 0x6a:(1,False), 0x6f:(0,False), 0x75:(73,False)}))
for ep, cs in endpoints.items():
    selected={0:(8,False),7:(4,False),0x000e:(endpoint_labels[ep],False)}
    if ep==1:
        selected.update({1:(2,False),3:(1,False),4:('DS',False),5:('bmssensor1',False),
                         0x4000:('1.1.0',False)})
    cs.insert(0,cluster(0,selected))
# Reuse the checked-in ZAP file as the container for regenerated endpoints.  The
# endpoint and endpoint-type arrays below are replaced in full, so no separate
# diagnostic-project template is needed to build from a clean checkout.
z=json.loads((BASE/'firmware/config/zcl/zcl_config.zap').read_text())
for p in z['package']:
    p['pathRelativity']='absolute'
    p['path']=str(BASE/'firmware/config/zcl/zcl-properties.json') if p['type']=='zcl-properties' else str(SDK/'protocol/zigbee/app/framework/gen-template/gen-templates.json')

properties=json.loads((SDK/'app/zcl/zcl-zap.json').read_text())
properties['xmlRoot']=[os.path.relpath(SDK/'app/zcl', BASE/'firmware/config/zcl'), '.']
properties['xmlFile'].append('analog-input.xml')
properties['xmlFile'].append('analog-value.xml')
(BASE/'firmware/config/zcl/zcl-properties.json').write_text(json.dumps(properties,indent=2)+'\n')
z['endpointTypes']=[]; z['endpoints']=[]
for ep, cs in sorted(endpoints.items()):
    name=f'BMS measurements {ep}'
    device=dict(code=12,profileId=260,label='HA Simple Sensor',name='HA-simplesensor',deviceTypeOrder=0)
    z['endpointTypes'].append(dict(id=ep,name=name,deviceTypeRef=device,deviceTypes=[device],deviceVersions=[1],deviceIdentifiers=[12],deviceTypeName='HA-simplesensor',deviceTypeCode=12,deviceTypeProfileId=260,clusters=cs))
    z['endpoints'].append(dict(endpointTypeName=name,endpointTypeIndex=ep-1,profileId=260,endpointId=ep,networkId=0,parentEndpointIdentifier=None))
(BASE/'firmware/config/zcl/zcl_config.zap').write_text(json.dumps(z,indent=2)+'\n')
(BASE/'results/endpoint-map.json').write_text(json.dumps(rows,indent=2)+'\n')
lines=['# Zigbee endpoint map','','Manufacturer: DS. Model: bmssensor1. Profile: Home Automation (0x0104).',
       'All BMS fields are read-only; Binary Input represents observed state, not a control.',
       'Endpoint 1 additionally exposes writable Analog Value (0x000e) PresentValue (0x0055):',
       'Update interval in whole seconds (5–3600), persisted in NVM3; EngineeringUnits is 73 (seconds).',
       'Every endpoint has Basic ProductLabel (0x000e), identifying its electrical/temperature source.',
       'Analog/Binary Input share endpoints independently and use Description for their field names.',
       'Analog/Binary Input and Analog Value descriptions are populated (48/16/48-byte limits).',
       'Optional/absent measurements retain invalid values.',
       '', '## Endpoint labels', '', '| Endpoint | ProductLabel |', '|---:|---|']
for ep, label in sorted(endpoint_labels.items()):
    lines.append(f'| {ep} | {label} |')
lines += ['', '## Measurements', '',
          '| Endpoint | Cluster | Attribute | Measurement | Register |','|---:|---|---|---|---|']
for m in rows:
    lines.append(f"| {m['endpoint']} | 0x{m['cluster']:04x} | 0x{m['attribute']:04x} | {m['name']} | 0x{m['reg']:04x} |")
(BASE/'ENDPOINTS.md').write_text('\n'.join(lines)+'\n')
header='''#ifndef BMS_METRICS_H
#define BMS_METRICS_H
#include <stdbool.h>
#include <stdint.h>
/* Compact description of a measurement and its standard ZCL destination. */
struct bms_metric {
    float scale;
    int16_t offset;
    uint16_t reg, mask, cluster, attribute, divisor;
    uint8_t endpoint, kind, shift, special;
};
'''
header += 'enum bms_metric_kind { '+', '.join('METRIC_'+k.upper() for k in kind_id)+' };\n'
header += f'#define BMS_METRIC_COUNT {len(rows)}\n'
header += '''extern const struct bms_metric bms_metrics[BMS_METRIC_COUNT];
bool bms_metric_value(const struct bms_metric *metric, float *value);
#endif
'''
(BASE/'src/bms_metrics.h').write_text(header)
c=['#include "bms_metrics.h"','','/* Generated by tools/generate.py; do not edit the table manually. */','const struct bms_metric bms_metrics[BMS_METRIC_COUNT] = {']
for m in rows:
    c.append('    { '+', '.join([f"{float(m['scale'])}f",str(m['offset']),hex(m['reg']),hex(m['mask']),hex(m['cluster']),hex(m['attribute']),str(m['divisor']),str(m['endpoint']),'METRIC_'+m['kind'].upper(),str(m['shift']),str(m['special'])])+' },')
c.append('};\n')
(BASE/'src/bms_metrics_table.c').write_text('\n'.join(c))
print(f'Generated {len(rows)} measurements on {len(endpoints)} endpoints')
