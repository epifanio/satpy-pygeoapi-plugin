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

Relative to your pygeoapi directory add this

`export PYGEOAPI_CONFIG=satpy-pygeoapi-plugin/etc/example-config.yml`

and

`export PYGEOAPI_OPENAPI=example-openapi.yml`

In your pygeoapi directory run something like this:

`pygeoapi openapi generate $PYGEOAPI_CONFIG --output-file $PYGEOAPI_OPENAPI`

This will from your openapi example config file generate the needed example-openapi.yaml file. The pygeoapi kan be started with:

`pygeoapi serve`
