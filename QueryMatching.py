#-------------------------------------------------------------------------------
# Name:        QueryMatching
# Purpose:
#
# Author:      simon scheider
#
# Created:     02/02/2017
# Copyright:   (c) simon 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------


import rdflib
import rdflib.plugins.sparql as sparql
import glob

def file_to_str(fn):
    """
    Loads the content of a text file into a string
    @return a string
    """
    with open(fn, 'r') as f:
        content=f.read()
    return content

def loadData(g, file ):
    wf = rdflib.Graph()
    gd = wf.parse(file, format='n3') +g
    print "data loaded"
    return gd

def loadQueries(filepattern):
    queries = []
    querystr = glob.glob(filepattern)
    #file = 'questions/maupquery.rq'
    for qi in querystr:
        print file_to_str(qi)
        q = sparql.prepareQuery(file_to_str('rdf_prefixes.txt') +'\n'+ file_to_str(qi))
        queries.append(q)
    return queries

class Stack:
     def __init__(self):
         self.items = []

     def isEmpty(self):
         return self.items == []

     def push(self, item):
         self.items.append(item)

     def pop(self):
         return self.items.pop()

     def peek(self):
         return self.items[len(self.items)-1]

     def size(self):
         return len(self.items)

class Outpattern():
    goals = []
    triples=[]
    rules = Stack()
    minus=[]
    completion=[]

    def __init__(self, goals=[], triples=[], rules=Stack()):
        #{"minus"=[], "completion"=[]}
        self.goals=goals
        self.triples=triples
        self.rules=rules

    def add(self, state, array=[]):
        if state == 'triples':
            self.triples.extend(array)
        elif state == 'minus':
            o = Outpattern(triples=array, rules=Stack())
            self.rules.push(o)
            print "write rule body: "+ str(array)
            #self.minus.append(array)
        elif state == 'completion':
            r = Outpattern(triples=array)
            o = self.rules.pop()
            o.rules.push(r)
            self.rules.push(o)
            print "write rule head: "+ str(array)
            #print "rule: "+ str(o.triples) + '->'+ str(r.triples)
            print "rule: "+ str(self.rules.items[0].triples) + '->'+ str(o.rules.items[0].triples)
            #state = 'triples'

    def __str__(self):
        rule = ''
        for index, p in enumerate(self.rules.items):
            rule += 'rule '+str(index) +': '
            rule += str(p.triples)
            comp = "EmptyQuery"
            if not p.rules.isEmpty():
                comp = p.rules.pop().triples
            rule += ' -> ' + str(comp) +'\n'
        return ('Output patterns: \n'+
        'goals: '+str(self.goals)+'\n'+
        'triples: '+str(self.triples)+'\n'+
        'rules: \n '+rule)
        #'completion: '+str(self.completion)+'\n')


#Method transforming queries into RDF
def parse2RDF(query):
    #get the SPARQL algebra
    a = query.algebra
    #print a
    goals=[]
    if 'PV' in a.keys():
        goals = a['PV']
        print "goals: " +str(goals)
    #initialize output object
    output = Outpattern(goals=goals)
    transformP(a.name, a, output, 'triples')
    return output

def transformP(pname, p, output, state):
    print 'parse: ' +pname
    if ((pname == 'part') or (pname=='graph') or (pname == 'GroupGraphPatternSub')):
        transformPart(p, output, state)
    elif pname =='Join':
        transformJoin(p, output, state)
    elif pname == 'TriplesBlock':
        transformTriplesBlock(p, output, state)
    elif pname == 'SelectQuery':
        if p.p:
            transformP(p.p.name,p.p, output, state)
    elif pname == 'Project':
        if p.p:
            transformP(p.p.name,p.p, output, state)
    elif pname == 'Filter':
        transformFilter(p, output, state)
    elif pname == 'BGP':
        transformBGP(p, output, state)
    else:
        print "This query contains the pattern "+pname+" which cannot be transformed!"

def transformTriplesBlock(pattern,output,state):
    triplesnew =[]
    for i in pattern.triples:
        tuple = (i[0],i[1],i[2])
        triplesnew.append(tuple)
    print 'push basic pattern '+pattern.name+': '+str(triplesnew) +' state:'+state
    output.add(state,triplesnew)

def transformBGP(pattern, output, state):
    print 'push basic pattern '+pattern.name+': '+str(pattern.triples)+' state:'+state
    output.add(state,pattern.triples)

def transformJoin(pattern, output, state):
    print 'transform a joined pattern'
    transformP(pattern.p1.name,pattern.p1,output, state)
    transformP(pattern.p2.name,pattern.p2,output, state)

def transformPart(parts, output, state):
    print "transform parts "#+str(parts)
    for partt in parts['part']:
        transformP(partt.name,partt,output, state)

def transformFilter(pattern, output, state):
    if pattern.p:
        transformP(pattern.p.name, pattern.p,output, state)
    filterexp = pattern.expr
    exname = filterexp.name
    print 'parse expression: '+exname
    transformExp(exname, filterexp,output, state)

def transformExp(exname,ex, output, state):
    if exname=='Builtin_NOTEXISTS':
        #print ex.keys()
       # print 'transform graph parts :'+str(ex.graph.part)
        print "graph: "+ex['graph'].name
        print "graph alt: "+ex.graph.name
        #print "graph content: "+str(ex['graph'])
        #print "graph2 content: "+str(ex.graph)
        #print "part :"+ex.graph.part.name
        if state == 'triples':
            state = 'minus'
        elif state =='minus':
            state = 'completion'
        transformP(ex['graph'].name,ex['graph'],output,state)
            #print part.triples
        if ex.graph.expr:
            print 'parse expression: '+ex.graph.expr.name
            transformExp(ex.graph.expr.name, ex.graph.expr,output, state)
    elif exname=='Builtin_EXISTS':
        print "graph: "+ex['graph'].name
        print "graph alt: "+ex.graph.name
        transformP(ex['graph'].name,ex['graph'],output,state)
            #print part.triples
        if ex.graph.expr:
            print 'parse expression: '+ex.graph.expr.name
            transformExp(ex.graph.expr.name, ex.graph.expr,output, state)
    elif exname=='RelationalExpression':
        if ('!' in ex.op or 'not' in ex.expr):
            #ex.op[]
            print "push relational pattern: " +str((ex.expr, ex.op, ex.other)) + 'state: ' +state
            output.add('minus',[(ex.expr, ex.op, ex.other)])

        print(str(ex.expr)+str(ex.op)+str(ex.other))
    elif exname == 'ConditionalAndExpression':
        print 'parse expression: '+ex['expr'].name
        transformExp(ex['expr'].name, ex['expr'],output, state)
        for o in ex['other']:
            print 'parse expression: '+o.name
            transformExp(o.name, o, output, state)
    else:
         print "This query contains expression "+exname+" which cannot be transformed!"















def main():
    #g = rdflib.ConjunctiveGraph()
    qs = loadQueries('questions/exampleQuery4.rq')
    for q in qs:
          sparql.algebra.pprintAlgebra(q)
          out = parse2RDF(q)
          print out
##        print q.algebra.keys()
##        print  q.algebra['_vars']
##        #print q.algebra['p']
##        print (q.algebra['p']).__class__.__name__
          #print q.algebra['PV']
##        #print q.algebra['datasetClause']
##        #sparql.algebra.pprintAlgebra(q)
##        print q.algebra.name
##        print q.algebra.p.name
##        print q.algebra.p.p.name
##        print q.algebra.p.p.p.name

        #p = test_test_{'fst':1, 'snd':2}

if __name__ == '__main__':
    main()
