import tokenize, token, types

SeqSep = object()
EndOfSeq = object()

class ObjectNotConvertable(Exception):
    pass

class SYSLib:
    def ISODate(self, data):
        o = {"jsonclass":["sys.ISODate", [data]]}
        return o
        
    
class JSONParser:
    def __init__(self):
        self.libs = {}
        self.allnames = []
        self.addLib(SYSLib(), "sys", ["ISODate"])
    
    def addLib(self, obj, name, exports):
        self.libs[name] = obj
        for n in exports:
            self.allnames.append("%s.%s" % (name, n))
    
    def objToJson(self, obj):
        """Serializes a python object to JSON.
        """
        try:
            return obj._toJSON()
        except:
            if type(obj) == types.DictionaryType:
                rslt = []
                for (key, val) in obj.items():
                    rslt.append('"%s":%s' % (key, self.objToJson(val)))
                return "{%s}" % ",".join(rslt)
            elif type(obj) in [types.ListType, types.TupleType]: 
                rslt = []
                for val in obj:
                    rslt.append(self.objToJson(val))
                return "[%s]" % ",".join(rslt)
            elif type(obj) == types.StringType:
                return repr(obj)
            elif type(obj) in[types.IntType, types.FloatType]:
                return str(obj)
            elif type(obj) == types.NoneType:
                return "null"
            else:
                raise ObjectNotConvertable()
    
    def jsonToObj(self, data):
        """Unmarshalls a String to a python object.
        
            It also makes sure that the data is indeed JSON conform.
        """
        lines = data.split("\n")
        def readline():
            try:
                l = lines.pop(0) + "\n"
                return l
            except:
                return ""
                
        tkns = tokenize.generate_tokens(readline)
        return self.parseValue(tkns)
    
    def parseValue(self, tkns):
        (ttype, tstr, ps, pe, lne) = tkns.next()
        if ttype in [token.STRING, token.NUMBER]:
            return eval(tstr)
        elif ttype == token.NAME:
            return self.parseName(tstr)
        elif ttype == token.OP:
            if tstr == "-":
                return - self.parseValue(tkns)
            elif tstr == "[":
                return self.parseArray(tkns)
            elif tstr == "{":
                return self.parseObj(tkns)
            elif tstr in ["}", "]"]:
                return EndOfSeq
            elif tstr == ",":
                return SeqSep
            else:
                raise "expected '[' or '{' but found: '%s'" % tstr 
        else:
            return EmptyValue
          
    def parseArray(self, tkns):
        a = [];
        try:
            while 1:
                v = self.parseValue(tkns)
                if v == EndOfSeq:
                    return a
                else:
                    a.append(v)
                    v = self.parseValue(tkns)
                    if v == EndOfSeq:
                        return a;
                    elif v != SeqSep:
                        raise"expected ',' but found: '%s'" % v 
        except:
            raise "expected ']'";
    
    def parseObj(self, tkns):
        obj = {}
        nme =""
        try:
            while 1:
                (ttype, tstr, ps, pe, lne) = tkns.next()
                if ttype == token.STRING:
                    nme =  eval(tstr)
                    (ttype, tstr, ps, pe, lne) = tkns.next()
                    if tstr == ":":
                        v = self.parseValue(tkns)
                        if v == SeqSep or v == EndOfSeq:
                            raise "value expected"
                        else:
                            obj[nme] = v;
                            v = self.parseValue(tkns)
                            if v == EndOfSeq:
                                return self.transformObj(obj);
                            elif not (v == SeqSep):
                                raise "',' expected"
                    else:
                        raise "':' expected but found: '%'";
                elif tstr == "}":
                    return self.transformObj(obj)
                else:
                    raise "String expected"
        except:
            raise #"expected '}'."
    
    def transformObj(self, obj):
        o2=None
        try:
            clsname =obj["jsonclass"][0]
            params =obj["jsonclass"][1]
            if clsname in self.allnames:
                libName = ".".join(clsname.split(".")[0:-1])
                clsname = clsname.split(".")[-1]
                constr = getattr(self.libs[libName], clsname)
                o2 = constr(*params)
                for (nme,val) in obj.items():
                    if not nme == "jsonclass":
                        setattr(o2, nme, val)
                return o2
            else:
                raise "jsonclass not found: " + clsName
        except:
            return obj
        
    def parseName(self, name):
        if name == "null":
            return None;
        if name == "true":
            return True;
        if name == "false":
            return False;
        else:
            raise "'null', 'true', 'false' expected but found: '%s'" % name;
    
    
parser = JSONParser()

def objToJson(obj):
    return parser.objToJson(obj)

def jsonToObj(data):
    return parser.jsonToObj(data)
    

