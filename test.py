import fastf1

event = fastf1.get_event(2024, "Spain")
session = event.get_session("Q")
session.load(telemetry=False, laps=True, weather=False)
q1_laps, q2_laps, q3_laps = session.laps.pick_drivers("VER").split_qualifying_sessions()

print(q1_laps['LapNumber'])
print("===")
print(q2_laps['LapNumber'])
print("===")
print(q3_laps['LapNumber'])


