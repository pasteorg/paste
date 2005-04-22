import os
from wsgikit import server
from wsgikit.pyconfig import Config
from wsgikit.configmiddleware import config_middleware
from wsgikit.webkit import wsgiwebkit

conf = Config()
conf.load_dict(server.default_ops, default=True)
conf.load_dict(@@other_conf@@)
server.load_conf(conf, @@default_config_fn@@)
if not conf.get('no_server_conf') and os.path.exists('server.conf'):
    server.load_conf(conf, 'server.conf')
if conf.get('config_file'):
    server.load_conf(conf, conf['config_file'])
if conf.get('sys_path'):
    server.update_sys_path(conf['sys_path'], conf['verbose'])

app = wsgiwebkit.webkit(conf['webkit_dir'], use_lint=conf.get('lint'))
app = config_middleware(app, conf)
