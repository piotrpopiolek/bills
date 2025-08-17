import multiprocessing

bind = "0.0.0.0:9100"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
proc_name = "bills-api"
preload_app = True
graceful_timeout = 30