# satpy-pygeoapi-plugin

Clone this repo and install with pip install .

This can then be configured into you pygeoapi with

```yaml
process-netcdf:
    type: process
    processor:
        name: satpy_pygeoapi_plugin.process_netcdf.ProcessNetcdfProcessor
```

Note: mapserver is required, but can only be found in conda-forge.
