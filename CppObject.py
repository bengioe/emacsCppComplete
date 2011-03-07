import sys
import subprocess
from xml.dom.minidom import parseString
import xml.dom.minidom as xml

class CppObject(object):
    instances = {}
    namedInstances = {}
    classes = []
    contextMap = {}
    dom = None
    def __init__(self,domelem,tagname):
        if domelem is None:
            return
        self.data = {}
        self.dom = domelem
        self.tag = tagname
        self.root= None
        self.demangled = None
        for k in domelem.attributes.keys():
            self.data[k]=domelem.getAttribute(k)
            #.attributes.get(k).nodeValue
        self.id = self.data['id']
        if tagname == "Class":
            CppObject.classes.append(self.data['demangled'])
            print "\nFound class",self.data['demangled'],self.fullname()
        if self.data.has_key("context"):
            ctx = self.data['context']
            if CppObject.contextMap.has_key(ctx):
                CppObject.contextMap[ctx].append(self)
            else:
                CppObject.contextMap[ctx] = [self]
        CppObject.namedInstances[self.fullname()] = self
        CppObject.instances[self.id] = self
    def getChildrenByWeakName(self,name):
        """
        get all the children which start with name
        """
        #we might be in a reference or pointer type
        # try to grab the parent:
        if not self.data.has_key('name') and self.root is not None:
            return CppObject.getById(
                self.root.getAttribute('id')).getChildrenByWeakName(name)
        print self.id
        print CppObject.contextMap[self.id]
        if CppObject.contextMap.has_key(self.id):
            children = CppObject.contextMap[self.id]
            return [i for i in children if i.shortname().startswith(name)]
        return []
    def __repr__(self):
        return self.fullname()
    def getType(self):
        if self.tag in ["Function","Method"]:
            c = CppObject.getById(self.data['returns'])
        if self.tag in ["Field"]:
            c = CppObject.getById(self.data['type'])
        #while not "name" in c.data.keys():
        #    c = CppObject.getById(c.data['type'])
        return c
    def shortname(self):
        return self.data['name']
    def fullname(self):
        if self.demangled is not None:
            return self.demangled
        try:
            if self.tag in ["Namespace","Class","Method","OperatorMethod","Constructor","Destructor"]:
                return self.data['demangled']
            return self.data['name']
        except Exception,e:
            try:
                name,elem = find_dom_name(CppObject.dom,self.data['type'])
                if self.tag=="ReferenceType":name+="&"
                if self.tag=="PointerType":name+="*"
                self.root = elem
                self.demangled = name
                return name
            except Exception,e:
                print e,self.tag
                return "error-name"
    def prettynames(self):
        if self.demangled is not None:
            return "cv",self.demangled,""
        if self.tag in ["Namespace","Class"]:
            return "::",self.data['demangled'],""
        if self.tag in ["Method","OperatorMethod"]:
            return ("()",
                    self.data['demangled'].replace(
                    CppObject.getById(self.data['context']).fullname()+"::",""),
                    CppObject.getById(self.data['returns']).fullname())
        if self.tag in ["Constructor","Destructor"]:
            return ("sp",self.data['demangled'].replace(
                    CppObject.getById(
                        self.data['context']).fullname()+"::",""),
                    "")
        if self.tag =="Field":
            return ("<>",
                    self.data['name'],
                    CppObject.getById(
                    self.data['type']).fullname())
        return "",self.data['name'],""
    @classmethod
    def addInstance(cls,i):
        #fn =i.fullname()
        #if not fn.startswith("std") and not fn.startswith("__"):
        #    print "added instance",fn
        cls.instances[i.id]=i
        cls.namedInstances[i.fullname()]=i
    @classmethod
    def getById(cls,i):
        return cls.instances[i]
    @classmethod
    def getByName(cls,i):
        return cls.namedInstances[i]
    @classmethod
    def getClassCandidates(cls,i):
        candidates = []
        for j in cls.classes:
            if i in j:
                candidates.append(j)
        return candidates
def find_dom_name(dom,tp):
    for elem in dom.childNodes:
        if isinstance(elem,xml.Element):
            if elem.hasAttribute('id') and elem.getAttribute('id')==tp:
                if elem.hasAttribute('demangled'):
                    return elem.getAttribute('demangled'),elem
                elif elem.hasAttribute('name'):
                    return elem.getAttribute('name'),elem
                else:
                    return find_dom_name(dom,elem.getAttribute('type'))
                    

def parse_file(header_data,cwd=None,inclDIRS=[]):
    incld = " ".join(["-I"+i for i in inclDIRS])
    handle = subprocess.Popen(("gccxml -I/usr/include/python2.6 "+incld+" -fxml=/dev/stdout").split(),
                              stdin =subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              cwd = cwd)
    handle.stdin.write(header_data)
    data = handle.communicate()[0]
    dom = parseString(data)
    dom = dom.childNodes[0]
    CppObject.dom = dom
    for elem in dom.childNodes:
        if isinstance(elem,xml.Element):
            tn = elem.tagName
            CppObject(elem,tn)

def parse_from_includes(file_data,cwd=None,inclDIRS=[]):
    includes =""
    for i in file_data.splitlines():
        if i.strip().startswith("#include"):
            includes+=i+"\n"
    parse_file(includes,cwd,inclDIRS)

if __name__=="__main__":
    import sys
    sys.argv.append("")
    if sys.argv[1]=="test":
        parse_from_includes(file("test.cpp",'r').read())
        c = CppObject.getByName("sf::Image")
        d= c.getChildrenByWeakName("Get")[0]
        print d
        print d.Type.fullname()
    elif sys.argv[1]=="xmltest":
        pass
    else:
        print "usage:\n\tpython CppObject.py [test|xmltest]"
