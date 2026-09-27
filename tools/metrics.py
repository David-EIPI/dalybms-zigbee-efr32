"""Declarative mapping of DALY values to standard Zigbee measurements."""
METRICS = []
def add(name, kind, reg, scale=1, offset=0, mask=65535, shift=0, special=0, unit=95):
    METRICS.append(dict(name=name, kind=kind, reg=reg, scale=scale, offset=offset,
                        mask=mask, shift=shift, special=special, unit=unit))

add('Pack voltage', 'voltage', 0x38, .1)
add('Pack current', 'current', 0x39, .1, -30000)
add('Charge current', 'current', 0x39, .1, -30000, special=1)
add('Discharge current', 'current', 0x39, .1, -30000, special=2)
add('State of charge', 'analog', 0x3a, .1, unit=98)
add('Register 003b raw', 'analog', 0x3b)
for i in range(8):
    add(f'Cell {i+1} voltage', 'voltage', i, .001, special=3)
    add(f'Cell {i+1} balancing', 'binary', 0x4f, mask=1, shift=i, special=4+i)
for i in range(8):
    add(f'Probe {i+1} temperature', 'temperature', 0x30+i, offset=-40, special=12+i)
for name, reg, scale, unit in [
    ('Cell count',0x3c,1,95), ('Probe count',0x3d,1,95),
    ('Highest voltage cell',0x3f,1,95), ('Lowest voltage cell',0x41,1,95),
    ('Hottest probe',0x44,1,95), ('Coldest probe',0x46,1,95),
    ('Temperature spread',0x47,1,62), ('Remaining Ah',0x4b,.1,95),
    ('Charge cycles',0x4c,1,95), ('BMS energy',0x59,1,18)]:
    add(name,'analog',reg,scale,unit=unit)
for name, reg in [('Highest cell voltage',0x3e), ('Lowest cell voltage',0x40), ('Cell voltage spread',0x42)]:
    add(name,'voltage',reg,.001)
for name, reg in [('Highest temperature',0x43), ('Lowest temperature',0x45),
                  ('MOS temperature',0x5a), ('Board temperature',0x5b), ('Heater temperature',0x5c)]:
    add(name,'temperature',reg,offset=-40)
add('Operating state (0 idle, 1 charge, 2 discharge)','analog',0x48)
add('Balancing current','current',0x4e,.001,-30000)
for name, reg in [('Balancing active',0x4d), ('Charge MOS active',0x52),
                  ('Discharge MOS active',0x53), ('Precharge MOS active',0x54),
                  ('Heater MOS active',0x55), ('Fan MOS active',0x56),
                  ('Charge MOS command',0x121), ('Discharge MOS command',0x122)]:
    add(name,'binary',reg)
for name, special in [('Pack power',20), ('Charge power',21), ('Discharge power',22)]:
    add(name,'power',0x58,special=special)
levels = ['Cell overvoltage','Cell undervoltage','Cell voltage difference','Charge overtemperature',
          'Charge undertemperature','Discharge overtemperature','Discharge undertemperature','Temperature difference',
          'Pack overvoltage','Pack undervoltage','Charge overcurrent','Discharge overcurrent',
          'Low state of charge','Low state of health','MOS overtemperature','Thermal runaway']
for i, name in enumerate(levels):
    byte = i // 2
    add(name+' alarm level','analog',0x6d+byte//2,mask=7,shift=(8 if byte%2 == 0 else 0)+(i%2)*3,special=23)
bits = {
 0:{6:'Smart charger connected',7:'Smart charger connection fault'},
 1:{6:'Smart discharger connected',7:'Smart discharger connection fault'},
 2:{6:'Charge MOS overtemperature fault',7:'Charge MOS temperature sensing fault'},
 3:{6:'Discharge MOS overtemperature fault',7:'Discharge MOS temperature sensing fault'},
 4:{6:'Short circuit protection',7:'Upgrade flag'},
 5:{6:'Charge undervoltage fault',7:'Discharge overvoltage fault'},
 6:{6:'Parallel communication active',7:'Parallel communication fault'},
 11:dict(enumerate(['AFE chip fault','AFE communication fault','AFE sampling fault','Cell voltage sensing fault',
                    'Cell voltage wire disconnected','Pack voltage sensing fault','Current sensing fault','Temperature sensing fault'])),
 12:dict(enumerate(['Temperature probe disconnected','EEPROM fault','Flash fault','RTC fault','Charge MOS fault',
                    'Discharge MOS fault','Precharge MOS fault','Precharge failure'])),
 13:dict(enumerate(['Charge MOS disabled by bus','Discharge MOS disabled by bus','Charge MOS disabled by switch',
                    'Discharge MOS disabled by switch','Fan active','Heater active','Current limiting active','Heater fault']))}
for byte, entries in bits.items():
    for bit, name in entries.items():
        add(name,'binary',0x6d+byte//2,mask=1,shift=(8 if byte%2 == 0 else 0)+bit)
add('BMS warnings','binary',0x6d,special=24)
add('BMS errors','binary',0x6d,special=25)
add('BMS communication','binary',0x38,special=26)
# Preserve undocumented optional values as explicitly raw values, not invented units.
for name, reg in [('Remaining mileage raw',0x5e), ('Charging time raw',0x64)]:
    add(name,'analog',reg)
for i in range(4):
    add(f'Legacy alarm register {0x66+i:04x} raw','analog',0x66+i)
for reg in (0x49, 0x4a, 0x50, 0x51, 0x57, 0x71):
    add(f'Register {reg:04x} raw', 'analog', reg)
