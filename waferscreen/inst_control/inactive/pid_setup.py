import adrcontrol

adr = adrcontrol.Adrcontrol()
adr.tempcontrol.PIDSetup()
adr.tempcontrol.SetTemperatureSetPoint(0.060)
