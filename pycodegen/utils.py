import inspect

def get_func_signature(func):
    args = inspect.getargspec(func)
    num_defaults = 0 if args.defaults is None else len(args.defaults)
    num_args =  len(args.args) - num_defaults

    _args = args.args[:num_args]
    if num_defaults:
        _defaults_pairs = zip(args.args[num_args:], args.defaults)
        _defaults = ["%s=%s" % (x, str(y)) for x, y in  _defaults_pairs]
        _args.extend( _defaults )
    if args.varargs:
        _args.append( '*%s' % args.varargs )
    if args.keywords:
        _args.append( '**%s' % args.keywords )
    return _args
