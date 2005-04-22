def simplehook():
    return 'calc'
simplehook.config_hook = True

def complexhook(context):
    return context
complexhook.config_hook = True

