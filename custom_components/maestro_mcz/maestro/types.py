"""Maestro MCZ Protocol Types and Constants."""
from enum import Enum
from dataclasses import dataclass

class MaestroMessageType(Enum):
    """Maestro message type. This information is inside the first frame."""
    Parameters = "00"
    Info = "01"
    Database = "02"
    ExtraParameters = "03"
    ChronoDays = "04"
    Alarms = "0A"
    WifiSonde = "0B"
    DatabaseName = "0D"
    SoftwareVersion = "0E"
    StringData = "AA"
    Ping = "PING"

@dataclass
class MaestroCommand:
    """Maestro Command definition."""
    name: str 
    id: int
    command_type: str
    category: str

@dataclass
class MaestroStoveState:
    """Maestro Stove State definition."""
    id: int
    description: str
    on_or_off: int # 0: Off, 1: On

@dataclass
class MaestroInformation:
    """Maestro Information definition."""
    id: int
    name: str
    message_type: str

# Commands List
MAESTRO_COMMANDS: list[MaestroCommand] = [
    MaestroCommand('Refresh', 0, 'Refresh', 'Daemon'),
    MaestroCommand('GetInfo', 0, 'GetInfo', 'GetInfo'),
    MaestroCommand('Temperature_Setpoint', 42, 'temperature', 'Basic'),
    MaestroCommand('Boiler_Setpoint', 51, 'temperature', 'Basic'),
    MaestroCommand('Chronostat', 1111, 'onoff', 'Basic'),
    MaestroCommand('Chronostat_T1', 1108, 'temperature', 'Basic'),
    MaestroCommand('Chronostat_T2', 1109, 'temperature', 'Basic'),
    MaestroCommand('Chronostat_T3', 1110, 'temperature', 'Basic'),
    MaestroCommand('Power_Level', 36, 'int', 'Basic'),
    MaestroCommand('Silent_Mode', 45, 'onoff', 'Basic'),
    MaestroCommand('Active_Mode', 35, 'onoff', 'Basic'),
    MaestroCommand('Eco_Mode', 41, 'onoff', 'Basic'),
    MaestroCommand('Sound_Effects', 50, 'onoff', 'Basic'),
    MaestroCommand('Power', 34, 'onoff40', 'Basic'),
    MaestroCommand('Fan_State', 37, 'int', 'Basic'),
    MaestroCommand('DuctedFan1', 38, 'int', 'Basic'),
    MaestroCommand('DuctedFan2', 39, 'int', 'Basic'),
    MaestroCommand('Control_Mode', 40, 'onoff', 'Basic'),
    MaestroCommand('Profile', 149, 'int', 'Basic'),
    # Untested
    MaestroCommand('Feeding_Screw', 34, '49', 'Basic'),
    MaestroCommand('Celsius_Fahrenheit', 49, 'int', 'Basic'),
    MaestroCommand('Sleep', 57, 'int', 'Basic'),
    MaestroCommand('Summer_Mode', 58, 'onoff', 'Basic'),
    MaestroCommand('Pellet_Sensor', 148, 'onoff', 'Basic'),
    MaestroCommand('Adaptive_Mode', 149, 'onoff', 'Basic'),
    MaestroCommand('AntiFreeze', 154, 'int', 'Basic'),
    MaestroCommand('Reset_Active', 2, '255', 'Basic'),
    MaestroCommand('Reset_Alarm', 1, '255', 'Basic'),
    # Diagnostics
    MaestroCommand('Diagnostics', 100, 'onoff', 'Diagnostics'),
    MaestroCommand('RPM_Fam_Fume', 1, 'int', 'Diagnostics'),
    MaestroCommand('RPM_WormWheel', 2, 'int', 'Diagnostics'),
    MaestroCommand('Active', 3, 'int', 'Diagnostics'),
    MaestroCommand('Ignitor', 4, 'onoff', 'Diagnostics'),
    MaestroCommand('FrontFan', 5, 'percentage', 'Diagnostics'),
    MaestroCommand('DuctedFan1', 6, 'percentage', 'Diagnostics'),
    MaestroCommand('DuctedFan2', 7, 'percentage', 'Diagnostics'),
    MaestroCommand('Pump_PWM', 8, 'percentage', 'Diagnostics'),
    MaestroCommand('3wayvalve', 9, 'onoff', 'Diagnostics'),
]

# Stove States
MAESTRO_STOVE_STATES: list[MaestroStoveState] = [
    MaestroStoveState(0, "Off", 0),
    MaestroStoveState(1, "Checking hot or cold", 1),
    MaestroStoveState(2, "Cleaning cold", 1),
    MaestroStoveState(3, "Loading Pellets Cold", 1),
    MaestroStoveState(4, "Start 1 Cold", 1),
    MaestroStoveState(5, "Start 2 Cold", 1),
    MaestroStoveState(6, "Cleaning Hot", 1),
    MaestroStoveState(7, "Loading Pellets Hot", 1),
    MaestroStoveState(8, "Start 1 Hot", 1),
    MaestroStoveState(9, "Start 2 Hot", 1),
    MaestroStoveState(10, "Stabilising", 1),
    MaestroStoveState(11, "Power 1", 1),
    MaestroStoveState(12, "Power 2", 1),
    MaestroStoveState(13, "Power 3", 1),
    MaestroStoveState(14, "Power 4", 1),
    MaestroStoveState(15, "Power 5", 1),
    MaestroStoveState(30, "Diagnostics", 0),
    MaestroStoveState(31, "On", 1),
    MaestroStoveState(40, "Extinguish", 1),
    MaestroStoveState(41, "Cooling", 1),
    MaestroStoveState(42, "Cleaning Low", 1),
    MaestroStoveState(43, "Cleaning High", 1),
    MaestroStoveState(44, "UNLOCKING SCREW", 0),
    MaestroStoveState(45, "Auto Eco", 0),
    MaestroStoveState(46, "Standby", 0),
    MaestroStoveState(48, "Diagnostics", 0),
    MaestroStoveState(49, "Loading Auger", 0),
    # Errors
    MaestroStoveState(50, "Error A01 - Ignition failed", 0),
    MaestroStoveState(51, "Error A02 - No flame", 0),
    MaestroStoveState(52, "Error A03 - Tank overheating", 0),
    MaestroStoveState(53, "Error A04 - Flue gas temperature too high", 0),
    MaestroStoveState(54, "Error A05 - Duct obstruction - Wind", 0),
    MaestroStoveState(55, "Error A06 - Bad printing", 0),
    MaestroStoveState(56, "Error A09 - SMOKE PROBE", 0),
    MaestroStoveState(57, "Error A11 - GEAR MOTOR", 0),
    MaestroStoveState(58, "Error A13 - MOTHERBOARD TEMPERATURE", 0),
    MaestroStoveState(59, "Error A14 - DEFECT ACTIVE", 0),
    MaestroStoveState(60, "Error A18 - WATER TEMP ALARM", 0),
    MaestroStoveState(61, "Error A19 - FAULTY WATER PROBE", 0),
    MaestroStoveState(62, "Error A20 - FAILURE OF AUXILIARY PROBE", 0),
    MaestroStoveState(63, "Error A21 - PRESSURE SWITCH ALARM", 0),
    MaestroStoveState(64, "Error A22 - ROOM PROBE FAULT", 0),
    MaestroStoveState(65, "Error A23 - BRAZIL CLOSING FAULT", 0),
    MaestroStoveState(66, "Error A12 - MOTOR REDUCER CONTROLLER FAILURE", 0),
    MaestroStoveState(67, "Error A17 - ENDLESS SCREW JAM", 0),
    MaestroStoveState(69, "WAITING FOR SECURITY ALARMS", 0),
]

# Information Fields (Position in Info Frame -> Definition)
# Note: Position 0 is likely MessageType, so index 1 is first data
MAESTRO_INFO: dict[int, MaestroInformation] = {
   1: MaestroInformation(1, "Stove_State", 'int'),
   2: MaestroInformation(2, "Fan_State", 'int'),
   3: MaestroInformation(3, "DuctedFan1", 'int'),
   4: MaestroInformation(4, "DuctedFan2", 'int'),
   5: MaestroInformation(5, "Fume_Temperature", 'temperature'),
   6: MaestroInformation(6, "Ambient_Temperature", 'temperature'),
   7: MaestroInformation(7, "Puffer_Temperature", 'temperature'),
   8: MaestroInformation(8, "Boiler_Temperature", 'temperature'),
   9: MaestroInformation(9, "NTC3_Temperature", 'temperature'),
   10: MaestroInformation(10, "Candle_Condition", 'int'),
   11: MaestroInformation(11, "Active_Set_Point", 'int'),
   12: MaestroInformation(12, "RPM_Fam_Fume", 'int'),
   13: MaestroInformation(13, "RPM_WormWheel", 'int'),
   14: MaestroInformation(14, "T3_Temperature", 'temperature'), # Back return
   # ... I will populate the rest based on assumption or need.
   # Many were not explicitly listed in the python dump I read but are implied by the iterator in process_infostring 
   # Actually the dump had some:
   52: MaestroInformation(52, "WifiSondeTemperature1", 'int'),
   53: MaestroInformation(53, "WifiSondeTemperature2", 'int'),
   54: MaestroInformation(54, "WifiSondeTemperature3", 'int'),
   55: MaestroInformation(55, "Unknown", 'int'),
   56: MaestroInformation(56, "SetPuffer", 'int'),
   57: MaestroInformation(57, "SetBoiler", 'int'),
   58: MaestroInformation(58, "SetHealth", 'int'),
   59: MaestroInformation(59, "Return_Temperature", 'temperature'),
   60: MaestroInformation(60, "AntiFreeze", 'onoff'),
}

# Derived commands (virtual)
MAESTRO_INFO[-1] = MaestroInformation(-1, "Power", 'onoff')
MAESTRO_INFO[-2] = MaestroInformation(-2, "Diagnostics", 'onoff')
