def full_eval(instance):
    def call(data, **metadata):
        x = instance(data, **metadata)
        if x is None:
            return None
        name, generator = x
        return name, list(generator)

    return call
