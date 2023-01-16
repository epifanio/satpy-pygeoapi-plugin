# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2022 Tom Kralidis
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import re
import os
import logging
import rasterio
import mapscript
from glob import glob
from satpy import Scene
from datetime import datetime

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError


LOGGER = logging.getLogger(__name__)

#: Process metadata and description
PROCESS_METADATA = {
    'version': '0.0.1',
    'id': 'process-netcdf',
    'title': {
        'en': 'netcdf',
        'fr': 'Bonjour le Monde'
    },
    'description': {
        'en': 'An example process that takes a name as input, and echoes '
              'it back as output. Intended to demonstrate a simple '
              'process with a single literal input.',
        'fr': 'Un exemple de processus qui prend un nom en entrée et le '
              'renvoie en sortie. Destiné à démontrer un processus '
              'simple avec une seule entrée littérale.',
    },
    'keywords': ['hello world', 'example', 'echo'],
    'links': [{
        'type': 'text/html',
        'rel': 'about',
        'title': 'information',
        'href': 'https://example.org/process',
        'hreflang': 'en-US'
    }],
    'inputs': {
        'name': {
            'title': 'Name',
            'description': 'The name of the person or entity that you wish to'
                           'be echoed back as an output',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'metadata': None,  # TODO how to use?
            'keywords': ['full name', 'personal']
        },
        'message': {
            'title': 'Message',
            'description': 'An optional message to echo as well',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 0,
            'maxOccurs': 1,
            'metadata': None,
            'keywords': ['message']
        }
    },
    'outputs': {
        'echo': {
            'title': 'Hello, world',
            'description': 'A "hello world" echo with the name and (optional)'
                           ' message submitted for processing',
            'schema': {
                'type': 'object',
                'contentMediaType': 'application/json'
            }
        }
    },
    'example': {
        'inputs': {
            'name': 'netcdf',
            'message': 'An optional message.',
            'netcdf_file': '/lustre/storeB/immutable/archive/projects/remotesensing/satellite-thredds/polar-swath/2023/01/13/noaa19-avhrr-20230113072221-20230113073600.nc'
        }
    }
}


class ProcessNetcdfProcessor(BaseProcessor):
    """Process NetCDF Processor example"""

    def __init__(self, processor_def):
        """
        Initialize object

        :param processor_def: provider definition

        :returns: pygeoapi.process.process_netcdf.ProcessNetcdfProcessor
        """

        super().__init__(processor_def, PROCESS_METADATA)

    def execute(self, data):

        mimetype = 'application/json'
        name = data.get('name')

        if name is None:
            raise ProcessorExecuteError('Cannot process without a name')

        message = data.get('message', '')
        print("MESSAGE", message)
        value = f'HelloXXXXXXXXXXXXXXXXXX {name}! {message}'.strip()

        netcdf_path = data.get('netcdf_file')
        value = f'{netcdf_path}'
        satpy_products = []
        full_request = None

        (_path, _platform_name, _, _start_time, _end_time) = _parse_filename(netcdf_path)
        start_time = datetime.strptime(_start_time, "%Y%m%d%H%M%S")
        print("START TIME: ", start_time)
        similar_netcdf_paths = _search_for_similar_netcdf_paths(_path, _platform_name, _start_time, _end_time)
        print("Similar netcdf paths:", similar_netcdf_paths)
        ms_satpy_products = _get_satpy_products(satpy_products, full_request)
        print("satpy product/layer", ms_satpy_products)

        satpy_products_to_generate = []
        for satpy_product in ms_satpy_products:
            satpy_product_filename = f'{satpy_product}-{start_time:%Y%m%d%H%M%S}.tif'
            satpy_products_to_generate.append({'satpy_product': satpy_product, 'satpy_product_filename': satpy_product_filename} )
        
        
        _generate_satpy_geotiff(similar_netcdf_paths, satpy_products_to_generate)

        map_object = mapscript.mapObj()
        _fill_metadata_to_mapfile(netcdf_path, map_object)

        for satpy_product in satpy_products_to_generate:
            layer = mapscript.layerObj()
            _generate_layer(start_time, satpy_product['satpy_product'],
                            satpy_product['satpy_product_filename'], layer)
            layer_no = map_object.insertLayer(layer)
        map_object.save(f'satpy-products-{start_time:%Y%m%d%H%M%S}.map')

        ows_req = mapscript.OWSRequest()
        ows_req.type = mapscript.MS_GET_REQUEST
        query_params = ("SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX=50,-10,80,50"
                        "&CRS=EPSG:4326&WIDTH=800&HEIGHT=1200&LAYERS=overview&"
                        "STYLES=&TIME=2023-01-13T07:22:21Z&FORMAT=image/png"
                        "&DPI=96&MAP_RESOLUTION=96&FORMAT_OPTIONS=dpi:96&"
                        "TRANSPARENT=TRUE")
        try:
            ows_req.loadParamsFromURL(query_params)
        except AttributeError:
            pass
        except mapscript.MapServerError:
            ows_req = mapscript.OWSRequest()
            ows_req.type = mapscript.MS_GET_REQUEST
            pass
        print("NumParams", ows_req.NumParams)
        print("TYPE", ows_req.type)

        mapscript.msIO_installStdoutToBuffer()
        map_object.OWSDispatch( ows_req )
        content_type = mapscript.msIO_stripStdoutBufferContentType()
        result = mapscript.msIO_getStdoutBufferBytes()

        # return mimetype, outputs
        print("CONTENT_TYPR", content_type)
        return content_type, result

    def __repr__(self):
        return f'<ProcessNetcdfProcessor> {self.name}'

def _parse_filename(netcdf_path):
    """Parse the netcdf to return start_time."""
    pattern_match = '^(.*satellite-thredds/polar-swath/\d{4}/\d{2}/\d{2}/)(metopa|metopb|metopc|noaa18|noaa19|noaa20|npp|aqua|terra|fy3d)-(avhrr|viirs-mband|viirs-dnb|modis-1km|mersi2-1k)-(\d{14})-(\d{14})\.nc$'
    pattern = re.compile(pattern_match)
    mtchs = pattern.match(netcdf_path)
    # start_time = None
    if mtchs:
        print("Pattern match:", mtchs.groups())
        # start_time = datetime.strptime(mtchs.groups()[5], "%Y%m%d%H%M%S")
        return mtchs.groups()
    return None

def _search_for_similar_netcdf_paths(path, platform_name, start_time, end_time):
    similar_netcdf_paths = glob(f'{path}{platform_name}-*-{start_time}-{end_time}.nc')
    return similar_netcdf_paths

def _get_satpy_products(satpy_products, full_request):
    """Get the product list to handle."""
    # Default
    ms_satpy_products = ['overview']
    # ms_satpy_products = ['night_overview']
    # if satpy_products:
    #     ms_satpy_products = satpy_products
    # else:
    #     try:
    #         ms_satpy_products = [full_request.query_params['layers']]
    #     except KeyError:
    #         try:
    #             ms_satpy_products = [full_request.query_params['LAYERS']]
    #         except KeyError:
    #             try:
    #                 ms_satpy_products = [full_request.query_params['layer']]
    #             except KeyError:
    #                 try:
    #                     ms_satpy_products = [full_request.query_params['LAYER']]
    #                 except KeyError:
    #                     pass
    return ms_satpy_products

def _generate_satpy_geotiff(netcdf_paths, satpy_products_to_generate):
    """Generate and save geotiff to local disk in omerc based on actual area."""
    satpy_products = []
    for _satpy_product in satpy_products_to_generate:
        if not os.path.exists(_satpy_product['satpy_product_filename']):
            satpy_products.append(_satpy_product['satpy_product'])
    if not satpy_products:
        print("No products needs to be generated.")
        return
    print(os.environ)
    print("Need to generate: ", satpy_products)
    print(datetime.now(), "Before Scene")
    swath_scene = Scene(filenames=netcdf_paths, reader='satpy_cf_nc')
    print(datetime.now(), "Before load")
    swath_scene.load(satpy_products)
    print("Available composites names:", swath_scene.available_composite_names())
    proj_dict = {'proj': 'omerc',
                 'ellps': 'WGS84'}

    print(datetime.now(), "Before compute optimal bb area")
    bb_area = swath_scene.coarsest_area().compute_optimal_bb_area(proj_dict=proj_dict, resolution=7500)
    #bb_area = swath_scene.coarsest_area().compute_optimal_bb_area(proj_dict=proj_dict)
    print(bb_area)
    print(bb_area.pixel_size_x)
    print(bb_area.pixel_size_y)
    
    print(datetime.now(), "Before resample")
    resample_scene = swath_scene.resample(bb_area)
    print(datetime.now(), "Before save")
    for _satpy_product in satpy_products_to_generate:
        if _satpy_product['satpy_product'] in satpy_products:
            resample_scene.save_dataset(_satpy_product['satpy_product'], filename=_satpy_product['satpy_product_filename'])
    print(datetime.now(), "After save")

def _fill_metadata_to_mapfile(netcdf_path, map_object):
    """"Add all needed web metadata to the generated map file."""
    map_object.web.metadata.set("wms_title", "WMS senda fastapi localhost")
    map_object.web.metadata.set("wms_onlineresource", f"http://localhost:8000/api/get_quicklook/{netcdf_path}")
    map_object.web.metadata.set("wms_srs", "EPSG:25833 EPSG:3978 EPSG:4326 EPSG:4269 EPSG:3857")
    map_object.web.metadata.set("wms_enable_request", "*")

    map_object.setProjection("AUTO")
    map_object.setSize(10000, 10000)
    map_object.units = mapscript.MS_DD

def _generate_layer(start_time, satpy_product, satpy_product_filename, layer):
    """Generate a layer based on the metadata from geotiff."""
    dataset = rasterio.open(satpy_product_filename)
    bounds = dataset.bounds
    ll_x = bounds[0]
    ll_y = bounds[1]
    ur_x = bounds[2]
    ur_y = bounds[3]

    layer.setProjection(dataset.crs.to_proj4())
    layer.status = 1
    layer.data = satpy_product_filename
    layer.type = mapscript.MS_LAYER_RASTER
    layer.name = satpy_product
    layer.metadata.set("wms_title", satpy_product)
    layer.metadata.set("wms_extent", f"{ll_x} {ll_y} {ur_x} {ur_y}")
    layer.metadata.set("wms_timeextent", f'{start_time:%Y-%m-%dT%H:%M:%S}Z/{start_time:%Y-%m-%dT%H:%M:%S}Z')
    layer.metadata.set("wms_default", f'{start_time:%Y-%m-%dT%H:%M:%S}Z')
    # layer.metadata.set("wms_srs", "EPSG:25833 EPSG:3978 EPSG:4326 EPSG:4269 EPSG:3857")
    # layer.units = mapscript.MS_DD
    dataset.close()
