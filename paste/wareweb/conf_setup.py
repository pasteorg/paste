from paste.webkit import conf_setup as webkit_conf_setup

def build_application(conf):
    conf['install_fake_webware'] = False
    return webkit_conf_setup.build_application(conf)
