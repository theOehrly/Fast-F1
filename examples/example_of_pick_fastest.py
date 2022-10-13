import fastf1
fastf1.Cache.enable_cache('D:/f1/f1py/cache') 
s=fastf1.get_session(2022,"austrian Grand Prix","Q")
s.load(messages=True)


print(s.laps.pick_driver("ALB").pick_fastest("Q1"))#to  compare check https://www.fia.com/sites/default/files/2022_11_aut_f1_q0_timing_qualifyingsessionlaptimes_v01.pdf