#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2023
#
# Author(s):
#
#   Trygve Aspenes <trygveas@met.no>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Movers for the move_it scripts."""

import re
import os
import base64
import logging
import rasterio
import mapscript
from glob import glob
from satpy import Scene
from datetime import datetime
from satpy_pygeoapi_plugin.celery import app
from celery import Task

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError

from satpy.utils import debug_on

debug_on()

LOGGER = logging.getLogger(__name__)

#: Process metadata and description
PROCESS_METADATA = {
    "version": "0.0.1",
    "id": "process-netcdf",
    "title": {"en": "netcdf", "fr": "Bonjour le Monde"},
    "description": {
        "en": "An example process that takes a name as input, and echoes "
        "it back as output. Intended to demonstrate a simple "
        "process with a single literal input.",
        "fr": "Un exemple de processus qui prend un nom en entrée et le "
        "renvoie en sortie. Destiné à démontrer un processus "
        "simple avec une seule entrée littérale.",
    },
    "keywords": ["hello world", "example", "echo"],
    "links": [
        {
            "type": "text/html",
            "rel": "about",
            "title": "information",
            "href": "https://example.org/process",
            "hreflang": "en-US",
        }
    ],
    "inputs": {
        "name": {
            "title": "Name",
            "description": "The name of the person or entity that you wish to"
            "be echoed back as an output",
            "schema": {"type": "string"},
            "minOccurs": 1,
            "maxOccurs": 1,
            "metadata": None,  # TODO how to use?
            "keywords": ["full name", "personal"],
        },
        "message": {
            "title": "Message",
            "description": "An optional message to echo as well",
            "schema": {"type": "string"},
            "minOccurs": 0,
            "maxOccurs": 1,
            "metadata": None,
            "keywords": ["message"],
        },
    },
    "outputs": {
        "echo": {
            "title": "Hello, world",
            "description": 'A "hello world" echo with the name and (optional)'
            " message submitted for processing",
            "schema": {"type": "object", "contentMediaType": "application/json"},
        }
    },
    "example": {
        "mode": "async",
        "inputs": {
            "name": "netcdf",
            "message": "An optional message.",
            "netcdf_file": "/pygeoapi/noaa19-avhrr-20230124115334-20230124120327.nc",
        },
    },
}


def _parse_filename(netcdf_path):
    print("########################################################")
    print(netcdf_path)
    print("########################################################")

    """Parse the netcdf to return start_time."""
    pattern_match = "^(.*)(metopa|metopb|metopc|noaa18|noaa19|noaa20|npp|aqua|terra|fy3d)-(avhrr|viirs-mband|viirs-dnb|modis-1km|mersi2-1k)-(\d{14})-(\d{14})\.nc$"
    pattern = re.compile(pattern_match)
    mtchs = pattern.match(netcdf_path)
    # start_time = None
    if mtchs:
        print("Pattern match:", mtchs.groups())
        # start_time = datetime.strptime(mtchs.groups()[5], "%Y%m%d%H%M%S")
        return mtchs.groups()
    return None


def _search_for_similar_netcdf_paths(path, platform_name, start_time, end_time):
    similar_netcdf_paths = glob(f"{path}{platform_name}-*-{start_time}-{end_time}.nc")
    return similar_netcdf_paths


def _get_satpy_products(satpy_products, full_request):
    """Get the product list to handle."""
    # Default
    ms_satpy_products = ["overview"]
    # ms_satpy_products = ['night_overview']
    if satpy_products:
        ms_satpy_products = satpy_products
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
        if not os.path.exists(_satpy_product["satpy_product_filename"]):
            satpy_products.append(_satpy_product["satpy_product"])
    if not satpy_products:
        print("No products needs to be generated.")
        return
    print(os.environ)
    print("Need to generate: ", satpy_products)
    print(datetime.now(), "Before Scene")
    print("####################### netcdf_paths ##########################")
    print(netcdf_paths)
    print("###############################################################")
    swath_scene = Scene(filenames=netcdf_paths, reader="satpy_cf_nc")
    print(datetime.now(), "Before load")
    swath_scene.load(satpy_products)
    print("Available composites names:", swath_scene.available_composite_names())
    proj_dict = {"proj": "omerc", "ellps": "WGS84"}

    print(datetime.now(), "Before compute optimal bb area")
    bb_area = swath_scene.coarsest_area().compute_optimal_bb_area(
        proj_dict=proj_dict, resolution=7500
    )
    # bb_area = swath_scene.coarsest_area().compute_optimal_bb_area(proj_dict=proj_dict)
    print(bb_area)
    print(bb_area.pixel_size_x)
    print(bb_area.pixel_size_y)

    print(datetime.now(), "Before resample")
    resample_scene = swath_scene.resample(bb_area)
    print(datetime.now(), "Before save")
    for _satpy_product in satpy_products_to_generate:
        if _satpy_product["satpy_product"] in satpy_products:
            resample_scene.save_dataset(
                _satpy_product["satpy_product"],
                filename=_satpy_product["satpy_product_filename"],
            )
    print(datetime.now(), "After save")


def _fill_metadata_to_mapfile(netcdf_path, map_object):
    """ "Add all needed web metadata to the generated map file."""
    map_object.web.metadata.set("wms_title", "WMS senda fastapi localhost")
    map_object.web.metadata.set(
        "wms_onlineresource", f"http://localhost:8000/api/get_quicklook/{netcdf_path}"
    )
    map_object.web.metadata.set(
        "wms_srs", "EPSG:25833 EPSG:3978 EPSG:4326 EPSG:4269 EPSG:3857"
    )
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
    layer.metadata.set(
        "wms_timeextent",
        f"{start_time:%Y-%m-%dT%H:%M:%S}Z/{start_time:%Y-%m-%dT%H:%M:%S}Z",
    )
    layer.metadata.set("wms_default", f"{start_time:%Y-%m-%dT%H:%M:%S}Z")
    # layer.metadata.set("wms_srs", "EPSG:25833 EPSG:3978 EPSG:4326 EPSG:4269 EPSG:3857")
    # layer.units = mapscript.MS_DD
    dataset.close()


class ProcessNetcdfProcessor(BaseProcessor, Task):
    """Process NetCDF Processor example"""

    def __init__(self, processor_def):
        """
        Initialize object

        :param processor_def: provider definition

        :returns: pygeoapi.process.process_netcdf.ProcessNetcdfProcessor
        """
        # print("processor def", processor_def)
        super().__init__(processor_def, PROCESS_METADATA)

    @app.task(track_started=True)
    def execute(self, data):
        mimetype = "application/json"
        name = data.get("name")
        if name is None:
            raise ProcessorExecuteError("Cannot process without a name")

        message = data.get("message", "")
        print("MESSAGE", message)
        value = f"HelloXXXXXXXXXXXXXXXXXX {name}! {message}".strip()

        netcdf_path = data.get("netcdf_file")
        value = f"{netcdf_path}"
        satpy_products = [data.get("layer", "overview")]
        full_request = None

        (_path, _platform_name, _, _start_time, _end_time) = _parse_filename(
            netcdf_path
        )
        start_time = datetime.strptime(_start_time, "%Y%m%d%H%M%S")
        print("START TIME: ", start_time)
        similar_netcdf_paths = _search_for_similar_netcdf_paths(
            _path, _platform_name, _start_time, _end_time
        )
        print("Similar netcdf paths:", similar_netcdf_paths)
        ms_satpy_products = _get_satpy_products(satpy_products, full_request)
        print("satpy product/layer", ms_satpy_products)

        satpy_products_to_generate = []
        for satpy_product in ms_satpy_products:
            satpy_product_filename = f"{satpy_product}-{start_time:%Y%m%d%H%M%S}.tif"
            satpy_products_to_generate.append(
                {
                    "satpy_product": satpy_product,
                    "satpy_product_filename": satpy_product_filename,
                }
            )

        _generate_satpy_geotiff(similar_netcdf_paths, satpy_products_to_generate)

        map_object = mapscript.mapObj()
        _fill_metadata_to_mapfile(netcdf_path, map_object)

        for satpy_product in satpy_products_to_generate:
            layer = mapscript.layerObj()
            _generate_layer(
                start_time,
                satpy_product["satpy_product"],
                satpy_product["satpy_product_filename"],
                layer,
            )
            layer_no = map_object.insertLayer(layer)
        map_object.save(f"satpy-products-{start_time:%Y%m%d%H%M%S}.map")

        bbox = "50,-10,80,50"
        bbox = "-1200000,6000000,3200000,9000000"
        epsg = "EPSG:4326"
        epsg = "EPSG:3857"
        time_stamp = "2023-01-13T07:22:21Z"
        ows_req = mapscript.OWSRequest()
        ows_req.type = mapscript.MS_GET_REQUEST
        query_params = (
            f"SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={bbox}"
            f"&CRS={epsg}&WIDTH=1200&HEIGHT=800&LAYERS={data.get('layer', 'overview')}&"
            f"STYLES=&TIME={time_stamp}&FORMAT=image/png"
            "&DPI=96&MAP_RESOLUTION=96&FORMAT_OPTIONS=dpi:96&"
            "TRANSPARENT=TRUE"
        )
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
        map_object.OWSDispatch(ows_req)
        content_type = mapscript.msIO_stripStdoutBufferContentType()
        result = mapscript.msIO_getStdoutBufferBytes()
        encoded_result = base64.b64encode(result)
        # return mimetype, outputs
        print("CONTENT_TYPR", content_type)
        return content_type, encoded_result.decode("ascii")

    def __repr__(self):
        return f"<ProcessNetcdfProcessor> {self.name}"


app.register_task(
    ProcessNetcdfProcessor(
        {"name": "satpy_pygeoapi_plugin.process_netcdf.ProcessNetcdfProcessor"}
    )
)
