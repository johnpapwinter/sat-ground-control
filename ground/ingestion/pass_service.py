import logging
import time

from redis import Redis
from skyfield.api import load, wgs84, EarthSatellite

log = logging.getLogger(__name__)


timescale = load.timescale()
ephemeris = load('de421.bsp')

line1 = '1 25544U 98067A   24040.51952315  .00016717  00000-0  30176-3 0  9990'
line2 = '2 25544  51.6415 162.4338 0005740  41.5244  35.8335 15.49479342438590'
satellite = EarthSatellite(line1, line2, 'SatSim-1', timescale)

ground_station = wgs84.latlon(+37.9838, +23.7275)


class PassService:
    def __init__(self, redis: Redis, satellite_id: int, poll_interval: float = 5.0) -> None:
        self.redis = redis
        self.satellite_id = satellite_id
        self.poll_interval = poll_interval

    def compute_visibility(self) -> bool:
        now = timescale.now()
        difference = satellite - ground_station
        topocentric = difference.at(now)
        alt, _, _ = topocentric.altaz()
        return alt.degrees > 0

    def run(self):
        log.info("Pass prediction service started")
        was_visible = False

        while True:
            is_visible = self.compute_visibility()
            self.redis.set(f"sat:{self.satellite_id}:visible", str(is_visible))

            if is_visible and not was_visible:
                log.info("Satellite AOS (acquisition of signal)")
                self.redis.publish("pass:event", "AOS")
            elif not is_visible and was_visible:
                log.info("Satellite LOS (loss of signal)")
                self.redis.publish("pass:event", "LOS")

            was_visible = is_visible
            time.sleep(self.poll_interval)

