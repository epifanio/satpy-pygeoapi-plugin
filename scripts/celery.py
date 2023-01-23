from celery import Celery

app = Celery('scripts',
            broker='redis://',
            backend='redis://',
            result_backend='redis://',
            result_extended=True,
            include=['satpy_pygeoapi_plugin.process_netcdf'])

app.conf.update(result_expires=3600,)

if __name__ == '__main__':
    # Optional configuration, see the application user guide.
    app.start()
