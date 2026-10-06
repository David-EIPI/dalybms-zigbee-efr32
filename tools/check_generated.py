"""Fail the build if ZAP drops endpoints or attributes during catalog import."""
import json
import re
from pathlib import Path
base=Path(__file__).resolve().parents[1]
rows=json.loads((base/'results/endpoint-map.json').read_text())
config=(base/'build/autogen/zap-config.h').read_text()
expected=len({m['endpoint'] for m in rows})
for macro,value in [('FIXED_ENDPOINT_COUNT',expected),('EMBER_AF_GENERATED_REPORTING_CONFIG_DEFAULTS_TABLE_SIZE',len(rows)+1)]:
    found=re.search(r'#define '+macro+r' \((\d+)\)',config)
    if not found or int(found[1]) != value:
        raise SystemExit(f'{macro}: expected {value}, generated {found[1] if found else "missing"}')
if 'ANALOG_INPUT_BASIC_CLUSTER' not in (base/'build/autogen/zap-id.h').read_text():
    raise SystemExit('Analog Input cluster missing')
print(f'Generated endpoint/report checks passed: {expected} endpoints, {len(rows)} values')

layout=json.loads((base/'results/attribute-layout.json').read_text())
setting=next(c for c in layout if c['endpoint']==1 and c['cluster']==0xe)
assert next(a['default'] for a in setting['attributes'] if a['id']==0x1c)=='Update interval'
assert next(a['default'] for a in setting['attributes'] if a['id']==0x75)=='73'
assert [(c['endpoint'],c['cluster'],a['id']) for c in layout for a in c['attributes']
        if a['writable']]==[(1,0xe,0x55)]
assert 'ANALOG_VALUE_BASIC_CLUSTER' in (base/'build/autogen/zap-id.h').read_text()
print('Writable Analog Value interval and seconds units verified')
for row in rows:
    entry=next(e for e in layout if e['endpoint']==row['endpoint'] and e['cluster']==row['cluster'])
    assert row['attribute'] in entry['attribute_ids']
    if row['cluster']==0xb04:
        expected={0,0xfffd}
        for sibling in rows:
            if sibling['endpoint']==row['endpoint'] and sibling['cluster']==0xb04:
                expected |= {sibling['attribute'],0x200+2*((sibling['attribute']-0x100)//3),0x201+2*((sibling['attribute']-0x100)//3)}
        assert set(entry['attribute_ids'])==expected, entry
print('Endpoint-specific attribute layout checks passed')

# Every queried register must have a mapping, including uninterpreted raw fields.
expected=set(range(8)) | set(range(0x30,0x48)) | set(range(0x48,0x5d)) | set(range(0x6d,0x74)) | {0x121,0x122,0x5e,0x64} | set(range(0x66,0x6a))
assert expected <= {m['reg'] for m in rows}, expected - {m['reg'] for m in rows}
print('Every queried register has a Zigbee mapping')

assert sum(c['cluster']!=0 for c in layout) <= 127, 'Binding-table capacity exceeded'
# Basic labels cover every endpoint; general inputs carry independent field names.
for ep in {m['endpoint'] for m in rows}:
    basic=next(c for c in layout if c['endpoint']==ep and c['cluster']==0)
    label=next(a['default'] for a in basic['attributes'] if a['id']==0x000e)
    assert label and len(label.encode())<=64
    assert all(m['product_label']==label for m in rows if m['endpoint']==ep)
for code, limit in [(0xc,48),(0xf,16)]:
    descriptions=[]
    for c in layout:
        if c['cluster']!=code: continue
        label=next(a['default'] for a in c['attributes'] if a['id']==0x1c)
        assert label.strip()==label and 0<len(label.encode())<=limit, label
        descriptions.append(label)
    assert len(descriptions)==len(set(descriptions)), 'Ambiguous general-cluster descriptions'
for cell in range(1,9):
    voltage=next(m for m in rows if m['name']==f'Cell {cell} voltage')
    assert voltage['endpoint']==cell+4 and voltage['product_label']==f'Cell {cell}'
# Keep general input endpoint identities stable across the naming upgrade.
for code in (0xc,0xf):
    entries=[m for m in rows if m['cluster']==code]
    assert [m['endpoint'] for m in entries]==list(range(1,len(entries)+1))
# Electrical/temperature clusters have no Description; their labels disambiguate them.
for code in (0xb04,0x402):
    labels={}
    for m in rows:
        if m['cluster']==code:
            previous=labels.setdefault(m['product_label'],m['endpoint'])
            assert previous==m['endpoint'], 'Ambiguous electrical/temperature source'
print('ProductLabel ownership and unique Analog/Binary Input descriptions verified')
