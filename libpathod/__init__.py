from tornado import web, template
import handlers, utils

class PathodApp(web.Application):
    def __init__(self, *args, **kwargs):
        self.templates = template.Loader(utils.data.path("templates"))
        web.Application.__init__(self, *args, **kwargs)


def application(**settings):
    return PathodApp(
                [
                    (r"/", handlers.Index),
                    (r"/log", handlers.Log),
                    (r"/help", handlers.Help),
                    (r"/preview", handlers.Preview),
                    (r"/p/.*", handlers.Pathod, settings),
                ],
                static_path = utils.data.path("static"),
                template_path = utils.data.path("templates"),
           )
