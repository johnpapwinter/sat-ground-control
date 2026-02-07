from skyfield.api import load, wgs84, EarthSatellite

timescale = load.timescale()
ephemeris = load('de421.bsp')


line1 = '1 25544U 98067A   24040.51952315  .00016717  00000-0  30176-3 0  9990'
line2 = '2 25544  51.6415 162.4338 0005740  41.5244  35.8335 15.49479342438590'
satellite = EarthSatellite(line1, line2, 'SatSim-1', timescale)

ground_station = wgs84.latlon(+37.9838, +23.7275)


def get_simulated_state():
    now = timescale.now()

    geocentric = satellite.at(now)

    is_sunlit = geocentric.is_sunlit(ephemeris)
    voltage = 28.0 if is_sunlit else 24.0

    difference = satellite - ground_station
    topocentric = difference.at(now)
    alt, az, distance = topocentric.altaz()
    is_visible = alt.degrees > 0

    return {
        "voltage": voltage,
        "is_visible": is_visible,
        "lat": wgs84.geographic_position_of(geocentric).latitude.degrees,
        "lon": wgs84.geographic_position_of(geocentric).longitude.degrees,
    }


print(get_simulated_state())
