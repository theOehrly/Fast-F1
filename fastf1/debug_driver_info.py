import fastf1
from fastf1.api import driver_info

fastf1.Cache.set_disabled()  # important: so the request is actually made

session = fastf1.get_session(2023, 11, 'Practice 1')
info = driver_info(session.api_path)

print(info)
