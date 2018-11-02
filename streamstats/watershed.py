# -*- coding: utf-8 -*-
"""Functionality for finding watershed information for specific locations."""

from streamstats import utils


class Watershed():
    """Watershed covering a spatial region, with associated information.

    The USGS StreamStats API is built around watersheds as organizational
    units. Watersheds in the 50 U.S. states can be found using lat/lon
    lookups, along with information about the watershed including its HUC code
    and a GeoJSON representation of the polygon of a watershed. Basin
    characteristics and flow statistics can also be extracted from watersheds.
    """
    base_url = "https://streamstats.usgs.gov/streamstatsservices/"

    def __init__(self, lat, lon):
        """Initialize a Watershed object

        :param lon: Longitude of point in decimal degrees.
        :type lon: float
        :param lat: Latitude of point in decimal degrees.
        :type lat: float
        :param simplify: Whether to simplify the polygon representation.
        :type simplify: bool
        """
        self.lat, self.lon = lat, lon
        self.address = utils.find_address(lat=lat, lon=lon)
        self.state = utils.find_state(self.address)
        self.data = self._delineate()
        self.workspace = self.data['workspaceID']
        self.flowstats = None

    def _delineate(self):
        """Find the watershed that contains a point.

        Implements a Delineate Watershed by Location query from
        https://streamstats.usgs.gov/docs/streamstatsservices/#/

        :rtype dict containing watershed data
        """
        payload = {
            'rcode': self.state,
            'xlocation': self.lon,
            'ylocation': self.lat,
            'crs': 4326,
            'includeparameters': True,
            'includeflowtypes': False,
            'includefeatures': True,
            'simplify': False
        }
        url = "".join((self.base_url, "watershed.geojson"))
        response = utils.requests_retry_session().get(url, params=payload)
        response.raise_for_status()  # raises errors early
        return response.json()

    def __repr__(self):
        """Get the string representation of a watershed."""
        huc = self.get_huc()
        huc_message = 'Watershed object with HUC%s: %s' % (len(huc), huc)
        coord_message = 'containing lat/lon: (%s, %s)' % (self.lat, self.lon)
        return ', '.join((huc_message, coord_message))

    def get_huc(self):
        """Find the Hydrologic Unit Code (HUC) of the watershed."""
        watershed_point = self.data['featurecollection'][0]['feature']
        huc = watershed_point['features'][0]['properties']['HUCID']
        return huc

    def get_boundary(self):
        """Return the full watershed GeoJSON as a dictionary"""
        # loop through the list of dictionaries and find the one named
        # 'globalwatershed', then return the feature dictionary from it
        for dictionary in self.data['featurecollection']:
            if dictionary.get('name', '') == 'globalwatershed':
                return dictionary['feature']

        # if we never found 'globalwatershed', something is wrong
        raise LookupError('Could not find "globalwatershed" in the feature'
                          'collection.')

    def available_characteristics(self):
        """List the available watershed characteristics."""
        raise NotImplementedError()

    def get_characteristics(self):
        """Get watershed characteristic data values."""
        raise NotImplementedError()

    def available_flow_stats(self):
        """List the available flow statistics

        :rtype list of available flow statistics
        """
        if not self.flowstats:
            self.get_flow_stats()
        avail_stats = [item['StatisticGroupName'] for item in self.flowstats]
        return avail_stats

    def get_flow_stats(self):
        """Get watershed flow statistics data values.

        :rtype dict containing flow statistics data for a watershed
        """
        pars = {
            'rcode': self.state,
            'workspaceID': self.workspace,
            'includeflowtypes': True
        }
        flow_url = "".join((self.base_url, 'flowstatistics.json'))
        response = utils.requests_retry_session().get(flow_url, params=pars)
        self.flowstats = response.json()
        return self.flowstats
