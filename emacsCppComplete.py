from Pymacs import lisp
import re
import CppObject as cpp
import time
import os
import os.path
import traceback

#matches a.b.c->d
#         ^ ^ <>
_re_conn = re.compile("(\.|->)")
#matches Class var (...)
#        <typ> <vn>
_re_def  = re.compile("(?P<nspace>[a-zA-Z0-9\_]+::){0,1}(?P<type>[a-zA-Z0-9\*\[\]\_]+)\s+(?P<vn>[a-zA-Z0-9\_]+)\(*.*\)*;")
#matches nested parentheses (asd,qwe(),zxc(jkl()))
#                           <                    >
#doesnt work... _re_nested_par = re.compile("(\((?>[^()]+|(?1))*\))")
_re_class_ns = re.compile("(?P<cname>[a-zA-Z0-9_]+)::[a-zA-Z0-9_]+\(.*\)[{]{0,1}")
#puts in a group the last word b4 "junk"
#e.g. "foo(bar"
#          < >
#_re_last_word = re.compile(".*(?P<w>[a-zA-Z0-9\_]+)$")
_re_last_word = re.compile("[^a-zA-Z0-9\_]*(?P<w>[a-zA-Z0-9\_]+)")

_re_namespace = re.compile("namespace\W+(?P<nspace>[a-zA-Z0-9]+)\W*")

def parse_lemacs(path):
    data = file(path,'r').read()
    r = {'include':[]}
    current_class = ""
    cwd = os.path.split(path)[0]
    for l in data.splitlines():
        if l.startswith("[") and l.endswith("]"):
            current_class=l[1:-1]
            continue
        if l.startswith("#"):continue
        if r.has_key(current_class):
            if current_class=="include" and l.startswith("."):
                r[current_class].append(cwd+"/"+l[1:])
                # since os.path.join doesnt seem to be working???
                continue
            r[current_class].append(l)
        else:
            r[current_class]=[l]
    return r

def update_state():
    lisp.message("Loading... this might take a while.")
    this_text = lisp.buffer_string()
    cwd = os.path.dirname(lisp.buffer_file_name())
    includes = []
    j = cwd
    while j!="/":
        p = os.path.join(j,".lemacs")
        if os.path.isfile(p):
            includes+=parse_lemacs(p)['include']
        j = os.path.join(os.path.split(j)[:-1])[0]
    cpp.parse_from_includes(this_text,cwd = cwd,inclDIRS = includes)
    lisp.message("Loaded auto-completion data!")
    
def command():
    c = lisp.completing_read("Enter command:",["update","reload","complete"])
    lisp.message(str(c))
    if c=="update" or c=="reload":
        update_state()
    elif c=="complete":
        complete_type()
command.interaction = ''

def rmargs(s):
    """
    hack to transform "foo(bar)" into "foo"
    not really classy, just kills after the first parenthesis "("
    """
    if '(' in s:
        return s[:s.index('(')]
    return s


def get_last_word(gp):
    """
    grab the last word from a group of words
    basically to tranform "bar(Vector foo,Matrix " into "Matrix "
    doesn't strip or anything, so beware :P
    """
    w = ""
    k = set(",=(")
    for i in gp[::-1]:
        if i not in k:
            w = i+w
        else:
            break
    return w
def try_cn_match(l,var):
    """
    Try to match a classname inside a line which would define 'var'
    say var is "toto"
    SomeFunction(SomeClass* toto);
    should return ["SomeClass"]
    """
    indexes = [i for i in range(len(l)) if l[i:].startswith(var)]
    cnames = []
    for i in indexes:
        k = list(l[:i])
        k.reverse()
        k = "".join(k)
        cname = ""
        for char in k:
            if char in ".:,;()":
                break
            cname=char+cname
        cnames.append(cname.replace("const","").replace("*","").replace("&","").strip())
    return cnames
def make_help_message(completions,help_str=""):
    slist = []
    for i in completions:
        slist.append(i.prettynames())# (attr,name,type)
    max1 = str(max([len(i[1]) for i in slist]))
    max2 = str(max([len(i[2]) for i in slist]))
    hlist = []
    s = "%3s %-"+max1+"s %"+max2+"s"
    for i in slist:
        print i
        hlist.append(s%i)
    hlist.sort()
    return help_str+"\n".join(hlist)

def check_word():
    line = lisp.buffer_substring(lisp.line_beginning_position(),lisp.point())
    lines= lisp.buffer_substring(1,lisp.point()).splitlines()
    lines.reverse()
    d = find_completion(line,lines)
    if d[0]:   
        f,completions,target = d
        #lisp.message("Found %d completions\n%s"%(len(completions),curType))
        
        help_str = make_help_message(completions)
        
        # make sure we're probably running X:
        if lisp.window_system() is not None and \
                lisp.pos_tip_show is not None: # make sure extension is installed
            lisp.pos_tip_show(help_str,None,None,None,0)
        else:
            lisp.message(help_str) # just use the emacs mini-buffer
        if len(completions)==1:#if there's only one completion, just insert it
            d = completions[0].data['name'][len(target):]
            if len(d):lisp.insert(d)     
    else:
        lisp.message(d[1])

def find_completion(line,buffer_lines):
    word = line
    # split "a.b->c"
    words = [i.strip() for i in _re_conn.split(word) if i not in ['','.','->']]
    if word.endswith(".") or word.endswith("->"):#e.g. "a.b."
        words.append('') # if the last element is 'nothing' then
        # we append an empty element which matches all completions
    if len(words)<=1:
        return (False,"Nothing to complete")
    
    #get the actual variable name, which should be the last "word" of the 
    #first part of the previous split.
    #example, line is: "foo(a.bar"
    # words should be: ["foo(a","bar"]
    # we therefore want "a" from "foo(a"
    var = get_last_word(words[0]).strip()
    print "base var is:",var
    # the target, "bar", which is what we're ultimately trying to complete.
    target = words[-1]
    curType = None# should also check for static class access
    potentialClassnames = []
    for l in buffer_lines:
        #we're looking for "Type var"
        if var in l:
            for classname in try_cn_match(l,var):
                if len(classname)==0:continue
                try:
                    #then check if it exists
                    cls = cpp.CppObject.getByName(classname)
                    curType = classname
                    break
                except KeyError:
                    potentialClassnames.append(classname)
                    # there might be an associated namespace
                    # here we're looking, for something like
                    # namespace NameSpace{
                    # then we're gonna look for NameSpace::Type
                    # which we might have found earlier
                    for L in buffer_lines:
                        defs = _re_namespace.search(L)
                        if defs:
                            nspace = defs.group('nspace')+"::"
                            try:
                                cls = cpp.CppObject.getByName(nspace+classname)
                                curType = nspace+classname
                                break
                            except:
                                pass
                except Exception,e:
                    print "##",e
        if curType is not None:
            break
    if curType is None: #nothing found, send a small error message:
        rlcls = [] #candidates
        for cls in potentialClassnames:
            cdts = cpp.CppObject.getClassCandidates(cls)
            rlcls.append([cdts,cls])
        s = "No definition of "+var+" found. (did you update?)"
        if len(rlcls):
            s+="\n Potential candidates:\n"
            for i in rlcls:
                for j in i[0]:
                    s+="\n  "+j+" for "+i[1]
        return (False,s)
    lastWord = ""
    def clean(s):
        return s.replace("*","").replace("[","").replace("]","").replace("&","").strip()
    try:
        curClass = cpp.CppObject.getByName(clean(curType))
    except KeyError,e:
        if curType!="!NoMatch":
            return (False,"Cannot complete type '"+curType+"' from "+lastWord)
        else:
            return (False,"No match for property "+lastWord)

    for i in words[1:]:
        #here we run through the stack of symbols, a.b->c.target
        #to find the final symbol's type (c's type in example above)
        try:
            curClass = cpp.CppObject.getByName(clean(curType))
            if i==target:
                break
        except KeyError,e:
            if curType!="!NoMatch":
                return (False,"Cannot complete type '"+curType+"' from "+lastWord)
            else:
                return (False,"No match for property "+lastWord)
        # we found a class
        lastType = curType
        curType = "!NoMatch"
        i = rmargs(i)
        lastWord = i
        # we're trying to find a children of this class(method or field)
        # which has the name of the next word
        # hopefully, there's only one, but in overloading
        # cases, it probably just won't work.
        # We'd need much better parsing than now.
        try:
            wordobj = curClass.getChildrenByWeakName(i)[0]
        except:
            return (False,"Cannot expand type '"+curType+"'")
        curType = wordobj.getType().fullname()
    # we ran through all the symbols, curClass is now "c"'s [return] type
    # and we can list all completions which start with "target"
    # (the original last word)
    try:
        completions = curClass.getChildrenByWeakName(target)
    except Exception,e:
        return (False,"Cannot expand type '"+curType+"' "+str(e))
    #return all of em
    if len(completions):
        return (True,completions,target)
    else:
        s = "No completions for %s.%s*, from %s"%(curType,target,str(curClass))
        return (False,s)
check_word.interaction = ''

def complete_type():
    c = lisp.completing_read("Type to complete:",cpp.CppObject.classes)
    lisp.message("Looking for:"+str(c))    
    try:
        t = cpp.CppObject.getByName(c)
        completions = t.getChildrenByWeakName("")
        lisp.pos_tip_show(make_help_message(completions),None,None,None,0)
    except:
        lisp.message("Couldn't find class "+c)
complete_type.interaction = ''

def ask(s):
    lisp.message("got:"+str(s))
ask.interaction = "s Enter str:"
