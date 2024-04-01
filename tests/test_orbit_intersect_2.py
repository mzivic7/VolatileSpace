from volatilespace.physics.orbit_intersect_debug import predict_enter_coi

print("testing predict_enter_coi()")
print("case: ellipse, same directions, vessel is faster")
print()

ecc = 0.6008720504761658
ma = 5.792703785429235
ea = 5.288975731201161
pea = 4.155140632859112
n = 0.0
a = 300.474848502583
b = 240.1831335461591
f = 180.5469383362623
per = 1463.5482795169676
dr = 1.0

b_ecc = 0.0542305694443186
b_ma = 5.692060439783578
b_ea = 0.0
b_pea = 6.137838350399759
b_n = 0.001997238120388435
b_a = 500.4608436404148
b_b = 499.7243854434846
b_f = 27.14027653520379
b_per = 0.0
b_dr = 1.0
coi = 99.85506614332527

center_x = -95.48276078172731
center_y = -153.23263143370454


vessel_data = (ecc, ma, ea, pea, n, a, b, f, per, dr)
body_data = (b_ecc, b_ma, b_ea, b_pea, b_n, b_a, b_b, b_f, b_per, b_dr, coi)
vessel_orbit_center = (center_x, center_y)

predict_enter_coi(vessel_data, body_data, vessel_orbit_center)
